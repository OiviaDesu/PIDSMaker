"""
Kairos Queue Detection Implementation
Paper: KAIROS §4.3-4.4
https://arxiv.org/abs/2308.05034

Implements time-window based queue detection with validation-driven threshold β.
"""

import math
import numpy as np
import pandas as pd
from collections import defaultdict
from typing import Dict, List, Set, Tuple
from pidsmaker.utils.utils import log, mean, std, listdir_sorted
import os


def compute_sigma_t_per_window(edge_losses: List[float], sigma_multiplier: float = 1.5) -> float:
    """
    Compute per-window threshold σT = mean + sigma_multiplier × SD
    Paper: KAIROS §4.3.1
    
    Args:
        edge_losses: List of reconstruction errors for edges in this time window
        sigma_multiplier: Multiplier for standard deviation (default: 1.5 per paper)
    
    Returns:
        σT threshold for this window
    """
    if len(edge_losses) == 0:
        return 0.0
    
    loss_mean = mean(edge_losses)
    loss_std = std(edge_losses)
    sigma_t = loss_mean + sigma_multiplier * loss_std
    
    return sigma_t


def compute_node_idf(graph_files: List[str]) -> Tuple[Dict[str, float], int]:
    """
    Compute IDF (Inverse Document Frequency) for nodes across graph files.
    IDF(node) = log(total_files / files_containing_node)
    Paper: KAIROS §4.3.1
    
    Args:
        graph_files: List of paths to graph files
    
    Returns:
        Tuple of (node_idf_dict, num_files)
    """
    import torch
    from tqdm import tqdm
    
    node_set = defaultdict(set)
    
    for f_path in tqdm(graph_files, desc="Computing node IDF"):
        try:
            g = torch.load(f_path)
            f_name = os.path.basename(f_path)
            
            for u, v, k in g.edges:
                # Extract node labels
                src_label = g.nodes[u].get("label", str(u))
                dst_label = g.nodes[v].get("label", str(v))
                
                node_set[src_label].add(f_name)
                node_set[dst_label].add(f_name)
        except Exception as e:
            log(f"Warning: Failed to load graph {f_path}: {e}")
            continue
    
    node_idf = {}
    num_files = len(graph_files)
    
    for node in node_set:
        include_count = len(node_set[node])
        idf = math.log(num_files / (include_count + 1))
        node_idf[node] = idf
    
    return node_idf, num_files


def filter_keywords(node_label: str) -> bool:
    """
    Filter out benign system nodes using keyword heuristics.
    Paper: KAIROS uses keyword filtering to reduce benign noise
    
    Args:
        node_label: Node label string
    
    Returns:
        True if node should be filtered (benign system node), False otherwise
    """
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
    
    for keyword in keywords:
        if keyword in node_label:
            return True
    return False


def extract_suspicious_nodes(
    edge_list: List[Tuple[str, str, float]],
    sigma_t: float,
    node_idf: Dict[str, float],
    num_files: int,
    idf_threshold_percentile: float = 0.9
) -> Set[str]:
    """
    Extract suspicious nodes from a time window.
    A node is suspicious if:
      1. It appears in edges with RE > σT
      2. It has high IDF (rare across dataset) - IDF > α
      3. It's not filtered by keywords
    
    Paper: KAIROS §4.3.1 - α (rareness threshold) is tunable, not fixed in paper.
    α is calibrated on validation data (e.g., as percentile of validation IDF distribution).
    
    Args:
        edge_list: List of (src_label, dst_label, loss) tuples
        sigma_t: Window-specific threshold
        node_idf: IDF values for all nodes
        num_files: Total number of files in dataset
        idf_threshold_percentile: α parameter - percentile for "high IDF" (tunable, paper §4.3.1)
    
    Returns:
        Set of suspicious node labels
    """
    suspicious_nodes = set()
    idf_threshold = math.log(num_files * idf_threshold_percentile / 1.0)
    
    for src_label, dst_label, loss in edge_list:
        if loss > sigma_t:
            # Check src node
            if not filter_keywords(src_label):
                src_idf = node_idf.get(src_label, math.log(num_files / 1.0))
                if src_idf > idf_threshold:
                    suspicious_nodes.add(src_label)
            
            # Check dst node
            if not filter_keywords(dst_label):
                dst_idf = node_idf.get(dst_label, math.log(num_files / 1.0))
                if dst_idf > idf_threshold:
                    suspicious_nodes.add(dst_label)
    
    return suspicious_nodes


def build_time_window_data(
    window_csv_path: str,
    node_idf: Dict[str, float],
    num_files: int,
    sigma_multiplier: float = 1.5,
    idf_threshold_percentile: float = 0.9
) -> Dict:
    """
    Build time window data structure from CSV file.
    
    Args:
        window_csv_path: Path to CSV file containing edge losses for this window
        node_idf: IDF values for nodes
        num_files: Total number of files
        sigma_multiplier: Multiplier for σT computation
    
    Returns:
        Dictionary with window metadata: name, σT, suspicious_nodes, mean_high_loss, edge_count
    """
    try:
        df = pd.read_csv(window_csv_path)
        
        # Extract losses
        losses = df["loss"].values.tolist()
        
        # Compute σT for this window
        sigma_t = compute_sigma_t_per_window(losses, sigma_multiplier)
        
        # Build edge list with labels
        edge_list = []
        for idx, row in df.iterrows():
            # Try to extract node labels from srcmsg/dstmsg or src/dst columns
            if "srcmsg" in df.columns and "dstmsg" in df.columns:
                try:
                    src_msg = eval(row["srcmsg"])
                    dst_msg = eval(row["dstmsg"])
                    src_label = list(src_msg.values())[0]
                    dst_label = list(dst_msg.values())[0]
                except:
                    src_label = str(row.get("src", idx))
                    dst_label = str(row.get("dst", idx))
            else:
                src_label = str(row.get("src", row.get("node_id", idx)))
                dst_label = str(row.get("dst", row.get("node_id", idx)))
            
            edge_list.append((src_label, dst_label, row["loss"]))
        
        # Extract suspicious nodes
        suspicious_nodes = extract_suspicious_nodes(
            edge_list, sigma_t, node_idf, num_files, idf_threshold_percentile
        )
        
        # Compute mean loss of high-RE edges
        high_re_losses = [loss for loss in losses if loss > sigma_t]
        mean_high_loss = mean(high_re_losses) if len(high_re_losses) > 0 else 0.0
        
        window_name = os.path.basename(window_csv_path)
        
        return {
            "name": window_name,
            "sigma_t": sigma_t,
            "suspicious_nodes": suspicious_nodes,
            "mean_high_loss": mean_high_loss,
            "edge_count": len(edge_list),
            "high_re_count": len(high_re_losses)
        }
    
    except Exception as e:
        log(f"Error processing window {window_csv_path}: {e}")
        return {
            "name": os.path.basename(window_csv_path),
            "sigma_t": 0.0,
            "suspicious_nodes": set(),
            "mean_high_loss": 0.0,
            "edge_count": 0,
            "high_re_count": 0
        }


def form_queues_by_overlap(windows: List[Dict], min_overlap: int = 1) -> List[List[Dict]]:
    """
    Form queues by correlating windows with overlapping suspicious nodes.
    Paper: KAIROS §4.3.2 - Windows are enqueued if they share suspicious nodes
    
    Args:
        windows: List of window dictionaries
        min_overlap: Minimum number of shared suspicious nodes to correlate (default: 1)
    
    Returns:
        List of queues, where each queue is a list of correlated windows
    """
    queues = []
    
    for window in windows:
        added_to_queue = False
        
        # Try to add to existing queue
        for queue in queues:
            for queue_window in queue:
                # Check overlap
                overlap = window["suspicious_nodes"] & queue_window["suspicious_nodes"]
                if len(overlap) >= min_overlap:
                    queue.append(window)
                    added_to_queue = True
                    break
            if added_to_queue:
                break
        
        # Create new queue if not added
        if not added_to_queue:
            queues.append([window])
    
    return queues


def compute_queue_anomaly_score_log(queue: List[Dict]) -> float:
    """
    Compute queue anomaly score in log space to avoid underflow.
    Score(queue) = Σᵢ log(mean_high_loss_i + 1)
    Paper: KAIROS §4.3.3 - Queue anomaly score is product of window scores
    
    Args:
        queue: List of window dictionaries
    
    Returns:
        Log-space queue anomaly score
    """
    log_score = 0.0
    for window in queue:
        # Add small constant to avoid log(0)
        log_score += math.log(window["mean_high_loss"] + 1.0)
    return log_score


def select_beta_from_validation(validation_queues: List[List[Dict]]) -> float:
    """
    Select threshold β from benign validation queues.
    β = max(validation queue scores) for 0% FPR on validation
    Paper: KAIROS §4.3.3
    
    Args:
        validation_queues: List of queues from benign validation data
    
    Returns:
        β threshold value (log-space)
    """
    if len(validation_queues) == 0:
        log("Warning: No validation queues found. Using default β = 0.0")
        return 0.0
    
    # Compute scores for all validation queues
    val_scores = [compute_queue_anomaly_score_log(queue) for queue in validation_queues]
    
    # β = max validation score (0% FPR on validation, per ORTHRUS-like strictness)
    beta = max(val_scores) if len(val_scores) > 0 else 0.0
    
    log(f"[Kairos Queue] β threshold from validation: {beta:.4f}")
    log(f"[Kairos Queue] Validation queue count: {len(validation_queues)}")
    log(f"[Kairos Queue] Validation score range: [{min(val_scores):.4f}, {max(val_scores):.4f}]")
    
    return beta


def flag_anomalous_queues(
    test_queues: List[List[Dict]],
    beta: float
) -> Tuple[List[int], List[float]]:
    """
    Flag test queues as anomalous if their score exceeds β.
    
    Args:
        test_queues: List of queues from test data
        beta: Threshold from validation
    
    Returns:
        Tuple of (anomalous_queue_indices, queue_scores)
    """
    anomalous_indices = []
    queue_scores = []
    
    for idx, queue in enumerate(test_queues):
        score = compute_queue_anomaly_score_log(queue)
        queue_scores.append(score)
        
        if score >= beta:
            anomalous_indices.append(idx)
            log(f"[Kairos Queue] Anomalous queue {idx}: score={score:.4f} ≥ β={beta:.4f}")
    
    log(f"[Kairos Queue] Flagged {len(anomalous_indices)}/{len(test_queues)} queues as anomalous")
    
    return anomalous_indices, queue_scores


def process_kairos_queue_detection(
    val_tw_path: str,
    test_tw_path: str,
    train_graph_files: List[str],
    test_graph_files: List[str],
    time_window_size: float = 15.0,
    neighborhood_size: int = 20,
    sigma_multiplier: float = 1.5,
    min_windows_per_queue: int = 2,
    idf_threshold_percentile: float = 0.9
) -> Dict:
    """
    Full Kairos queue detection pipeline.
    
    Args:
        val_tw_path: Path to validation time-window CSV files
        test_tw_path: Path to test time-window CSV files
        train_graph_files: List of training graph file paths (for IDF)
        test_graph_files: List of test graph file paths (for IDF)
        time_window_size: Window size in minutes (default: 15 per paper §4.3)
        neighborhood_size: Neighborhood size |N| (default: 20 per paper §4.3)
        sigma_multiplier: Multiplier for σT (default: 1.5 per paper §4.3.1)
        min_windows_per_queue: Minimum windows to form a queue (default: 2)
        idf_threshold_percentile: α parameter for "high IDF" threshold (tunable per paper §4.3.1)
    
    Returns:
        Dictionary with detection results: beta, val_queues, test_queues, anomalous_indices
    """
    log(f"\n{'='*60}")
    log("KAIROS Queue Detection Pipeline")
    log(f"{'='*60}")
    
    # Step 1: Compute IDF for nodes
    log("\n[Step 1/5] Computing node IDF from training data...")
    train_node_idf, num_train_files = compute_node_idf(train_graph_files)
    test_node_idf, num_test_files = compute_node_idf(test_graph_files)
    log(f"  Train IDF: {len(train_node_idf)} unique nodes across {num_train_files} files")
    log(f"  Test IDF: {len(test_node_idf)} unique nodes across {num_test_files} files")
    
    # Combine IDFs (use train+test for better coverage per paper)
    combined_idf = {**train_node_idf, **test_node_idf}
    combined_num_files = max(num_train_files, num_test_files)
    
    # Step 2: Build validation windows and form queues
    log("\n[Step 2/5] Building validation time-window queues...")
    val_files = sorted([os.path.join(val_tw_path, f) for f in listdir_sorted(val_tw_path)])
    val_windows = []
    for window_file in val_files:
        window_data = build_time_window_data(
            window_file, combined_idf, combined_num_files, sigma_multiplier, idf_threshold_percentile
        )
        val_windows.append(window_data)
        log(f"  {window_data['name']}: σT={window_data['sigma_t']:.4f}, "
            f"suspicious_nodes={len(window_data['suspicious_nodes'])}, "
            f"high_RE={window_data['high_re_count']}/{window_data['edge_count']}")
    
    val_queues = form_queues_by_overlap(val_windows)
    
    # Filter queues by minimum size
    val_queues = [q for q in val_queues if len(q) >= min_windows_per_queue]
    log(f"  Formed {len(val_queues)} validation queues (min_windows={min_windows_per_queue})")
    
    # Step 3: Select β from validation
    log("\n[Step 3/5] Selecting threshold β from validation queues...")
    beta = select_beta_from_validation(val_queues)
    
    # Step 4: Build test windows and form queues
    log("\n[Step 4/5] Building test time-window queues...")
    test_files = sorted([os.path.join(test_tw_path, f) for f in listdir_sorted(test_tw_path)])
    test_windows = []
    for window_file in test_files:
        window_data = build_time_window_data(
            window_file, combined_idf, combined_num_files, sigma_multiplier, idf_threshold_percentile
        )
        test_windows.append(window_data)
    
    test_queues = form_queues_by_overlap(test_windows)
    test_queues = [q for q in test_queues if len(q) >= min_windows_per_queue]
    log(f"  Formed {len(test_queues)} test queues")
    
    # Step 5: Flag anomalous queues
    log("\n[Step 5/5] Flagging anomalous queues with β threshold...")
    anomalous_indices, queue_scores = flag_anomalous_queues(test_queues, beta)
    
    log(f"\n{'='*60}")
    log(f"KAIROS Queue Detection Complete")
    log(f"  β threshold: {beta:.4f}")
    log(f"  Anomalous queues: {len(anomalous_indices)}/{len(test_queues)}")
    log(f"{'='*60}\n")
    
    return {
        "beta": beta,
        "val_queues": val_queues,
        "test_queues": test_queues,
        "anomalous_indices": anomalous_indices,
        "queue_scores": queue_scores,
        "test_windows": test_windows
    }


# Wrapper function that accepts cfg object (for compatibility with queue_evaluation.py)
def process_kairos_queue_detection_from_cfg(cfg):
    """
    Wrapper for process_kairos_queue_detection that extracts parameters from config object.
    
    Args:
        cfg: Configuration object
    
    Returns:
        Dictionary with detection results
    """
    # Extract idf_threshold_percentile from config (default 0.9 if not specified)
    idf_threshold_percentile = 0.9  # Default value
    if hasattr(cfg.detection.evaluation.queue_evaluation, 'kairos_idf_queue'):
        kairos_config = cfg.detection.evaluation.queue_evaluation.kairos_idf_queue
        if hasattr(kairos_config, 'idf_threshold_percentile'):
            idf_threshold_percentile = kairos_config.idf_threshold_percentile
            log(f"[Kairos Config] Using α (IDF threshold percentile): {idf_threshold_percentile}")
    
    # TODO: Extract other parameters and call process_kairos_queue_detection
    # This wrapper needs to be implemented based on how cfg provides paths and graph files
    raise NotImplementedError(
        "process_kairos_queue_detection_from_cfg needs implementation. "
        "Call process_kairos_queue_detection directly with extracted parameters."
    )
