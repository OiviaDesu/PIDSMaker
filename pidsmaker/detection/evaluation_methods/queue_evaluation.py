import copy
import math
import os
import re
from collections import defaultdict

import torch
import tqdm
import wandb
from sklearn.neighbors import LocalOutlierFactor

from pidsmaker.detection.evaluation_methods.evaluation_utils import (
    classifier_evaluation,
    compute_tw_labels,
)
from pidsmaker.detection.evaluation_methods.kairos_queue_detection import (
    process_kairos_queue_detection,
    process_kairos_queue_detection_from_cfg,
)
from pidsmaker.utils.utils import (
    get_all_files_from_folders,
    listdir_sorted,
    log,
    mean,
    percentile_90,
    std,
)


# Kairos code
def cal_idf_kairos(graph_files):
    node_set = defaultdict(set)
    for f_path in tqdm(graph_files, desc="Calculating IDF"):
        g = torch.load(f_path)

        f_path = f_path.split("/")[-1]
        for u, v, k in g.edges:
            node_set[g.nodes[u]["label"]].add(f_path)
            node_set[g.nodes[v]["label"]].add(f_path)

    node_IDF = {}
    for n in node_set:
        include_count = len(node_set[n])
        # PAPER-ALIGNED: IDF(v) = ln(N/(N_v+1)) per KAIROS §4.3.1
        IDF = math.log(len(graph_files) / (include_count + 1))
        node_IDF[n] = IDF

    return node_IDF, len(graph_files)


def is_include_key_word_bak(s):
    keywords = [
        ":",
        "null",
        "/dev/pts",
        "salt-minion.log",
        "675",
        "usr",
        "proc",
        "/.cache/mozilla/",
        "tmp",
        "thunderbird",
        "/bin/",
        "/sbin/sysctl",
        "/data/replay_logdb/",
        "/home/admin/eraseme",
        "/stat",
    ]
    flag = False
    for i in keywords:
        if i in s:
            flag = True
    return flag


def is_include_key_word(s):
    keywords = [
        ":",
        "/dev/pts",
        "salt-minion.log",
        "null",
        "usr",
        "proc",
        "firefox",
        "tmp",
        "thunderbird",
        "bin/",
        "/data/replay_logdb",
        "/stat",
        "/boot",
        "qt-opensource-linux-x64",
        "/eraseme",
        "675",
    ]
    flag = False
    for i in keywords:
        if i in s:
            flag = True
    return flag


def cal_set_rel_bak(node_IDF, s1, s2, num_files):
    new_s = (
        s1 & s2
    )  # used to find common nodes in two windows to check if they should be in the same queue
    count = 0
    for i in new_s:
        #     jdata=json.loads(i)
        if is_include_key_word_bak(i) is not True:
            if i in node_IDF.keys():
                IDF = node_IDF[i]
            else:
                IDF = math.log(num_files / (1))

            if (IDF) > math.log(
                num_files * 0.9 / (1)
            ):  # TODO: default value for kairos, but can be parametrized
                log("node:", i, " IDF:", IDF)
                count += 1
    return count


def cal_set_rel(train_node_IDF, test_node_IDF, s1, s2, num_test_files, num_train_files):
    IDF_train = train_node_IDF
    new_s = (
        s1 & s2
    )  # used to find common nodes in two windows to check if they should be in the same queue
    count = 0
    for i in new_s:
        if is_include_key_word(i) is not True:
            if i in test_node_IDF:
                IDF_test = test_node_IDF[i]
            else:
                IDF_test = math.log(num_test_files / (1))

            if i in train_node_IDF:
                IDF_train = train_node_IDF[i]
            else:
                IDF_train = math.log(num_train_files / (1))

            if (
                IDF_test + IDF_train
            ) > 5:  # PAPER-ALIGNED: IDF rareness threshold α per KAIROS §4.3.1 (configurable)
                log(f"node: {i} | IDF test: {IDF_test:.3f} | IDF train: {IDF_train:.3f}")
                count += 1
    return count


def cal_anomaly_loss_kairos(loss_list, edge_list):
    if len(loss_list) != len(edge_list):
        log("error!")
        return 0
    count = 0
    loss_sum = 0
    loss_std = std(loss_list)
    loss_mean = mean(loss_list)
    edge_set = set()
    node_set = set()
    node2redundant = {}

    # PAPER-ALIGNED: Per-window cutoff σT = mean + 1.5*SD (KAIROS §4.3.1)
    thr = loss_mean + 1.5 * loss_std

    log("thr:", thr)

    for i in range(len(loss_list)):
        if loss_list[i] > thr:
            count += 1
            src_node = edge_list[i][0]
            dst_node = edge_list[i][1]

            loss_sum += loss_list[i]

            node_set.add(src_node)
            node_set.add(dst_node)
            edge_set.add(edge_list[i][0] + edge_list[i][1])
    return count, loss_sum / (count + 0.00000000001), node_set, edge_set


def anomalous_queue_construction_kairos(
    test_tw_path, train_node_IDF, test_node_IDF, num_train_files, num_test_files, cfg
):
    # check if we use val set here

    queues = []
    his_tw = {}
    current_tw = {}
    index_count = 0

    files = listdir_sorted(test_tw_path)
    for f_path in files:
        f = open(os.path.join(test_tw_path, f_path))
        edge_loss_list = []
        edge_list = []
        log("index_count:", index_count)

        for line in f:
            l = line.strip()
            jdata = eval(l)
            edge_loss_list.append(jdata["loss"])
            src_msg = list(eval(jdata["srcmsg"]).values())[
                0
            ]  # transform "subject: /etc/.." to "/etc/.."
            dst_msg = list(eval(jdata["dstmsg"]).values())[0]
            edge_list.append([src_msg, dst_msg])
        count, loss_avg, node_set, edge_set = cal_anomaly_loss_kairos(edge_loss_list, edge_list)
        current_tw = {}
        current_tw["name"] = f_path
        current_tw["loss"] = loss_avg
        current_tw["index"] = index_count
        current_tw["nodeset"] = node_set

        # PAPER-ALIGNED: Queue construction by suspicious node overlap (KAIROS §4.3.2)
        # If S_Tnew ∩ S_T ≠ ∅ for any T in queue q, append to q; else start new queue
        added_que_flag = False
        for hq in queues:
            for his_tw in hq:
                if cfg.detection.evaluation.queue_evaluation.kairos_idf_queue.include_test_set_in_IDF:
                    cal_re = cal_set_rel(
                        train_node_IDF,
                        test_node_IDF,
                        current_tw["nodeset"],
                        his_tw["nodeset"],
                        num_test_files,
                        num_train_files,
                    )
                else:
                    cal_re = cal_set_rel_bak(
                        train_node_IDF, current_tw["nodeset"], his_tw["nodeset"], num_train_files
                    )
                if cal_re != 0 and current_tw["name"] != his_tw["name"]:
                    hq.append(copy.deepcopy(current_tw))
                    added_que_flag = True
                    break
            if added_que_flag:
                break
        if added_que_flag is False:
            temp_hq = [copy.deepcopy(current_tw)]
            queues.append(temp_hq)
        index_count += 1
        log(
            f_path,
            "  ",
            loss_avg,
            " count:",
            count,
            " percentage:",
            count / len(edge_list),
            " node count:",
            len(node_set),
            " edge count:",
            len(edge_set),
        )

    return queues


def create_queues_kairos(cfg):
    # In kairos, IDF is computed only on benign edges (train set)
    base_dir = cfg.preprocessing.transformation._graphs_dir
    train_feat_files = get_all_files_from_folders(base_dir, cfg.dataset.train_files)
    test_feat_files = get_all_files_from_folders(base_dir, cfg.dataset.test_files)

    train_node_IDF, num_train_files = cal_idf_kairos(train_feat_files)
    test_node_IDF, num_test_files = cal_idf_kairos(test_feat_files)

    test_losses_dir = os.path.join(cfg.detection.gnn_training._edge_losses_dir, "test")
    for model_epoch_dir in tqdm(listdir_sorted(test_losses_dir), desc="Building queues"):
        log(f"\nEvaluation of model {model_epoch_dir}...")
        test_tw_path = os.path.join(test_losses_dir, model_epoch_dir)
        queues = anomalous_queue_construction_kairos(
            test_tw_path, train_node_IDF, test_node_IDF, num_train_files, num_test_files, cfg
        )

        out_dir = cfg.detection.evaluation.queue_evaluation._queues_dir
        os.makedirs(out_dir, exist_ok=True)
        torch.save(queues, os.path.join(out_dir, f"{model_epoch_dir}_queues.pkl"))


# Provnet code
def cal_val_thr(graph_dir):
    filelist = listdir_sorted(graph_dir)

    loss_list = []
    for i in sorted(filelist):
        f = open(os.path.join(graph_dir, i))
        for line in f:
            l = line.strip()
            jdata = eval(l)

            loss_list.append(jdata["loss"])

    thr = max(loss_list)
    log(
        f"Thr = {thr}, Avg = {mean(loss_list)}, STD = {std(loss_list)}, MAX = {max(loss_list)}, 90 Percentile = {percentile_90(loss_list)}"
    )

    return thr


def cal_anomaly_loss_with_val_threshold(loss_list, edge_list, thr):
    count = 0
    loss_sum = 0

    edge_set = set()
    node_set = set()

    for i in range(len(loss_list)):
        if loss_list[i] > thr:
            count += 1

            # node_info = (node_id, node_label)
            src_node_info = edge_list[i][0]
            dst_node_info = edge_list[i][1]
            loss_sum += loss_list[i]

            node_set.add(src_node_info)
            node_set.add(dst_node_info)
            edge_set.add(edge_list[i][0] + edge_list[i][1])

    if count == 0:
        return 0, 0, node_set, edge_set
    else:
        return count, loss_sum / count, node_set, edge_set


# Measure the relationship between two time windows, if the returned value
# is not 0, it means there are suspicious nodes in both time windows.


def cal_set_rel_lof(s1, s2, lof_model, nodelabels_train_val, node2vec):
    new_s = s1 & s2
    count = 0
    for i in new_s:
        # i => (node_id, node_label)
        i = i[1]
        if "netflow" in i:
            continue

        # if path name is not in the training and validation sets
        # OutlierScore = (¬ exist) * LOF
        if i in nodelabels_train_val:
            lof_score = 0
        else:
            try:
                i = eval(i)
            except:
                log(i)
                exit()
            if "subject" in i:
                path = i["subject"]
            elif "file" in i:
                path = i["file"]

            try:
                emb = node2vec[path]
            except Exception as error:
                log(f"Error at {i}: {error}")
                continue
                # exit() #TODO: handle this

            lof_score = lof_model.decision_function([emb])

        if lof_score < 0:
            log(f"node:{i}, LOF score:{lof_score}")
            count += 1
    return count


def anomalous_queue_construction_provnet(
    graph_dir_path, lof_model=None, nodelabels_train_val=None, node2vec=None, val_thr=None
):
    queues = []
    current_tw = {}

    file_l = listdir_sorted(graph_dir_path)
    index_count = 0
    for f_path in sorted(file_l):
        log(f"Time window at index {index_count}: {f_path}")

        f = open(f"{graph_dir_path}/{f_path}")
        edge_loss_list = []
        edge_list = []

        # Figure out which nodes are anomalous in this time window
        for line in f:
            l = line.strip()
            jdata = eval(l)
            edge_loss_list.append(jdata["loss"])
            edge_list.append(
                [
                    (str(jdata["srcnode"]), str(jdata["srcmsg"])),
                    (str(jdata["dstnode"]), str(jdata["dstmsg"])),
                ]
            )

        count, loss_avg, node_set, edge_set = cal_anomaly_loss_with_val_threshold(
            edge_loss_list, edge_list, val_thr
        )
        current_tw["name"] = f_path
        current_tw["loss"] = loss_avg
        current_tw["index"] = index_count
        current_tw["nodeset"] = node_set

        # Incrementally construct the queues
        added_que_flag = False
        for hq in queues:
            for his_tw in hq:
                cal_set_rel_results = cal_set_rel_lof(
                    current_tw["nodeset"],
                    his_tw["nodeset"],
                    lof_model,
                    nodelabels_train_val,
                    node2vec,
                )
                if cal_set_rel_results != 0 and current_tw["name"] != his_tw["name"]:
                    hq.append(copy.deepcopy(current_tw))
                    added_que_flag = True
                    break
        if added_que_flag is False:
            temp_hq = [copy.deepcopy(current_tw)]
            queues.append(temp_hq)

        index_count += 1

        log(
            f"Avg loss: {loss_avg} | Anomalies in time window: ({len(node_set)} and {len(edge_set)} malicious nodes and edges)\n"
        )

    return queues


def train_lof_model(cfg):
    node2vec_train_val_path = os.path.join(
        cfg.featurization.feat_training.alacarte._vec_graphs_dir, "nodelabel2vec_val"
    )
    labels_and_embeddings = torch.load(node2vec_train_val_path)

    embeddings = []
    for label in labels_and_embeddings:
        # We don't consider network
        if ":" in label:
            continue
        else:
            embeddings.append(labels_and_embeddings[label])

    clf = LocalOutlierFactor(novelty=True, n_neighbors=30).fit(embeddings)
    torch.save(clf, os.path.join(cfg.detection.evaluation._task_path, "trained_lof.pkl"))
    return clf


def ground_truth_label(test_tw_path, cfg):
    labels = []
    for _ in listdir_sorted(test_tw_path):
        labels.append(0)

    if cfg._test_mode:
        return labels

    tw_to_malicious_nodes = compute_tw_labels(cfg)
    for tw, nodes in tw_to_malicious_nodes.items():
        labels[tw] = 1

    return labels


def create_queues_provnet(cfg):
    node2vec_path = os.path.join(
        cfg.featurization.feat_training.alacarte._vec_graphs_dir, "nodelabel2vec"
    )
    node2vec_train_val_path = os.path.join(
        cfg.featurization.feat_training.alacarte._vec_graphs_dir, "nodelabel2vec_val"
    )

    node2vec = torch.load(node2vec_path)
    nodelabels_train_val = list(torch.load(node2vec_train_val_path).keys())

    lof_model = train_lof_model(cfg)

    test_losses_dir = os.path.join(cfg.detection.gnn_training._edge_losses_dir, "test")
    val_losses_dir = os.path.join(cfg.detection.gnn_training._edge_losses_dir, "val")

    for model_epoch_dir in listdir_sorted(test_losses_dir):
        log(f"\nEvaluation of model {model_epoch_dir}...")
        test_tw_path = os.path.join(test_losses_dir, model_epoch_dir)
        val_tw_path = os.path.join(val_losses_dir, model_epoch_dir)

        # Threshold
        val_thr = cal_val_thr(val_tw_path)

        # Testing date
        queues = anomalous_queue_construction_provnet(
            graph_dir_path=test_tw_path,
            lof_model=lof_model,
            nodelabels_train_val=nodelabels_train_val,
            node2vec=None,
            val_thr=val_thr,
        )

        out_dir = cfg.detection.evaluation.queue_evaluation._queues_dir
        os.makedirs(out_dir, exist_ok=True)
        torch.save(queues, os.path.join(out_dir, f"{model_epoch_dir}_queues.pkl"))


def predict_queues(cfg):
    # Evaluating the testing set
    test_losses_dir = os.path.join(cfg.detection.gnn_training._edge_losses_dir, "test")

    best_precision, best_stats = 0.0, None
    for model_epoch_dir in listdir_sorted(test_losses_dir):
        test_tw_path = os.path.join(test_losses_dir, model_epoch_dir)

        pred_label = []
        for _ in range(len(listdir_sorted(test_tw_path))):
            pred_label.append(0)

        queues = torch.load(
            os.path.join(
                cfg.detection.evaluation.queue_evaluation._queues_dir,
                f"{model_epoch_dir}_queues.pkl",
            )
        )
        labels = ground_truth_label(test_tw_path, cfg)

        detected_queues = []
        for queue in queues:
            label = any([labels[hq["index"]] for hq in queue])
            # PAPER-ALIGNED: Queue score = product of time-window scores (KAIROS §4.3.3)
            # Note: Using (loss+1) to avoid zero; paper uses product in log-space
            anomaly_score = 0
            for hq in queue:
                if anomaly_score == 0:
                    anomaly_score = (anomaly_score + 1) * (hq["loss"] + 1)
                else:
                    anomaly_score = (anomaly_score) * (hq["loss"] + 1)
            log(f"-> queue anomaly score: {anomaly_score:.2f} | {'ATTACK' if label else ''}")

            if anomaly_score > cfg.detection.evaluation.queue_evaluation.queue_threshold:
                idx_list = []
                for i in queue:
                    idx_list.append(i["index"])
                log(f"Anomalous queue: {idx_list}")
                detected_queues.append(idx_list)
                for i in idx_list:
                    pred_label[i] = 1
                log(f"Anomaly score: {anomaly_score}")

        out_dir = cfg.detection.evaluation.queue_evaluation._predicted_queues_dir
        os.makedirs(out_dir, exist_ok=True)
        torch.save(
            detected_queues, os.path.join(out_dir, f"{model_epoch_dir}_predicted_queues.pkl")
        )

        # Calculate the metrics
        log("\n********************************* Attack Labels *********************************")

        stats = classifier_evaluation(labels, pred_label, pred_label)
        stats["epoch"] = int(re.findall(r"[+-]?\d*\.?\d+", model_epoch_dir)[0])
        wandb.log(stats)

        if stats["precision"] > best_precision:
            best_precision = stats["precision"]
            best_stats = stats
        elif str(stats["precision"]) == "nan":
            best_precision = 0
            best_stats = stats

    wandb.log(best_stats)


def evaluate_kairos_phase_one(cfg, results_by_epoch):
    if not results_by_epoch:
        log("[Kairos Queue] No results generated during Phase 1 queue detection.")
        return results_by_epoch

    test_losses_dir = os.path.join(cfg.detection.gnn_training._edge_losses_dir, "test")
    if not os.path.isdir(test_losses_dir):
        log(
            f"[Kairos Queue] Test edge losses directory missing ({test_losses_dir}); cannot compute metrics."
        )
        return results_by_epoch

    os.makedirs(cfg.detection.evaluation.queue_evaluation._predicted_queues_dir, exist_ok=True)
    os.makedirs(cfg.detection.evaluation.queue_evaluation._kairos_dir, exist_ok=True)

    best_precision, best_stats = 0.0, None

    for model_epoch_dir in listdir_sorted(test_losses_dir):
        result = results_by_epoch.get(model_epoch_dir)
        if result is None:
            log(
                f"[Kairos Queue] No detection results for epoch {model_epoch_dir}; skipping metric computation."
            )
            continue

        test_tw_path = os.path.join(test_losses_dir, model_epoch_dir)
        labels = ground_truth_label(test_tw_path, cfg)
        num_windows = len(labels)

        test_windows = result.get("test_windows", [])
        window_name_to_index = {w.get("name"): w.get("index") for w in test_windows}

        pred_label = [0] * num_windows
        detected_queues = []

        test_queues = result.get("test_queues", [])
        anomalous_indices = result.get("anomalous_indices", [])

        for queue_idx in anomalous_indices:
            if queue_idx >= len(test_queues):
                log(
                    f"[Kairos Queue] Queue index {queue_idx} out of range for epoch {model_epoch_dir}."
                )
                continue

            queue = test_queues[queue_idx]
            queue_window_indices = set()

            for window in queue:
                idx = window.get("index")
                if idx is None and "name" in window:
                    idx = window_name_to_index.get(window["name"])
                if idx is None:
                    try:
                        idx = test_windows.index(window)
                    except ValueError:
                        idx = None
                if idx is None or idx >= num_windows or idx < 0:
                    continue
                pred_label[idx] = 1
                queue_window_indices.add(idx)

            detected_queues.append(sorted(queue_window_indices))

        stats = classifier_evaluation(labels, pred_label, pred_label)
        stats["epoch"] = int(re.findall(r"[+-]?\d*\.?\d+", model_epoch_dir)[0])
        stats["kairos_beta"] = float(result.get("beta", 0.0))

        queue_scores = result.get("queue_scores", [])
        stats["kairos_queue_score_max"] = float(max(queue_scores)) if queue_scores else 0.0
        stats["kairos_queue_score_mean"] = (
            float(mean(queue_scores)) if queue_scores else 0.0
        )
        stats["kairos_anomalous_queue_count"] = len(anomalous_indices)

        wandb.log(stats)

        if stats["precision"] > best_precision:
            best_precision = stats["precision"]
            best_stats = stats
        elif str(stats["precision"]) == "nan":
            best_precision = 0
            best_stats = stats

        torch.save(
            detected_queues,
            os.path.join(
                cfg.detection.evaluation.queue_evaluation._predicted_queues_dir,
                f"{model_epoch_dir}_predicted_queues.pkl",
            ),
        )

        epoch_artifact_dir = os.path.join(
            cfg.detection.evaluation.queue_evaluation._kairos_dir, model_epoch_dir
        )
        os.makedirs(epoch_artifact_dir, exist_ok=True)
        torch.save(result, os.path.join(epoch_artifact_dir, "results.pt"))

    if best_stats is not None:
        wandb.log(best_stats)

    return results_by_epoch


def main(cfg):
    method = cfg.detection.evaluation.queue_evaluation.used_method

    if method == "kairos_idf_queue":
        # Check if using Phase 1 paper-faithful implementation
        if hasattr(cfg.detection.evaluation.queue_evaluation.kairos_idf_queue, 'include_test_set_in_IDF'):
            # NEW: Phase 1 paper-faithful Kairos queue detection
            log("[Queue-level] Using Kairos Phase 1 queue detection (paper-faithful)")
            results_by_epoch = process_kairos_queue_detection_from_cfg(cfg)
            return evaluate_kairos_phase_one(cfg, results_by_epoch)
        else:
            # Original Kairos implementation
            create_queues_kairos(cfg)
            predict_queues(cfg)
    elif method == "provnet_lof_queue":
        create_queues_provnet(cfg)
        predict_queues(cfg)
    else:
        raise ValueError(f"Invalid queue evaluation method `{method}`")
