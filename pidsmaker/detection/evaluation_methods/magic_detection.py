"""
MAGIC KNN-based Outlier Detection Implementation
Paper: MAGIC §4.3-4.4, §6.3
https://www.usenix.org/conference/usenixsecurity24/presentation/jia

Implements KNN outlier detection with validation-driven threshold θ and adaptation.
"""

import numpy as np
import pandas as pd
import torch
from sklearn.neighbors import NearestNeighbors
from typing import Dict, List, Tuple, Optional
import os
from pidsmaker.utils.utils import log, listdir_sorted


def extract_node_embeddings(model, graph_batch, device='cpu') -> torch.Tensor:
    """
    Extract node embeddings from MAGIC masked GAT encoder.
    Paper: MAGIC §4.2 - Node embeddings from masked graph auto-encoder
    
    Args:
        model: Trained MAGIC model with encoder
        graph_batch: PyTorch Geometric graph batch
        device: Device to run on
    
    Returns:
        Node embeddings tensor [num_nodes, embedding_dim]
    """
    model.eval()
    with torch.no_grad():
        # Forward pass through encoder
        if hasattr(model, 'encoder'):
            embeddings = model.encoder(
                graph_batch.x.to(device),
                graph_batch.edge_index.to(device)
            )
        elif hasattr(model, 'forward'):
            # Some models return (embeddings, reconstructed_features, ...)
            output = model(
                graph_batch.x.to(device),
                graph_batch.edge_index.to(device)
            )
            if isinstance(output, tuple):
                embeddings = output[0]  # First output is usually embeddings
            else:
                embeddings = output
        else:
            raise ValueError("Model must have 'encoder' or 'forward' method")
        
        return embeddings.cpu()


def build_knn_index(embeddings: np.ndarray, k: int = 20, algorithm: str = 'ball_tree') -> NearestNeighbors:
    """
    Build KNN index for outlier detection.
    Paper: MAGIC §4.3 - KNN-based outlier detector
    
    Args:
        embeddings: Node embeddings [num_nodes, embedding_dim]
        k: Number of nearest neighbors (default: 20)
        algorithm: Algorithm for KNN ('ball_tree', 'kd_tree', 'brute')
    
    Returns:
        Fitted NearestNeighbors object
    """
    nbrs = NearestNeighbors(n_neighbors=min(k, len(embeddings)), algorithm=algorithm, metric='euclidean')
    nbrs.fit(embeddings)
    
    log(f"[Magic KNN] Built KNN index: {len(embeddings)} nodes, k={k}, algorithm={algorithm}")
    
    return nbrs


def compute_knn_outlier_scores(
    embeddings: np.ndarray,
    knn_index: NearestNeighbors
) -> np.ndarray:
    """
    Compute KNN outlier scores as mean distance to k nearest neighbors.
    Paper: MAGIC §4.3 - Outlier score based on KNN distance
    
    Args:
        embeddings: Node embeddings [num_nodes, embedding_dim]
        knn_index: Fitted KNN index
    
    Returns:
        Outlier scores [num_nodes]
    """
    distances, indices = knn_index.kneighbors(embeddings)
    
    # Outlier score = mean distance to k nearest neighbors
    outlier_scores = np.mean(distances, axis=1)
    
    return outlier_scores


def sweep_validation_threshold(
    val_scores: np.ndarray,
    val_labels: np.ndarray,
    target_fpr: float = 0.01,
    percentile_range: Tuple[int, int] = (90, 99.9)
) -> Dict:
    """
    Sweep validation scores to find threshold θ with FPR ≤ target_fpr.
    Paper: MAGIC §4.3-4.4 - Threshold selection on benign validation
    
    Args:
        val_scores: Validation outlier scores [num_val_nodes]
        val_labels: Validation ground truth labels (0=benign, 1=malicious)
        target_fpr: Target false positive rate (default: 0.01 = 1%)
        percentile_range: Range of percentiles to sweep (default: 90-99.9)
    
    Returns:
        Dictionary with: theta, percentile, val_fpr, val_tpr
    """
    # Generate candidate thresholds from percentiles
    percentiles = np.linspace(percentile_range[0], percentile_range[1], 100)
    candidate_thresholds = np.percentile(val_scores, percentiles)
    
    best_theta = None
    best_percentile = None
    best_fpr = 1.0
    
    for percentile, theta in zip(percentiles, candidate_thresholds):
        # Predict: flag nodes with score > theta
        predictions = (val_scores > theta).astype(int)
        
        # Compute FPR and TPR
        tn = np.sum((predictions == 0) & (val_labels == 0))
        fp = np.sum((predictions == 1) & (val_labels == 0))
        fn = np.sum((predictions == 0) & (val_labels == 1))
        tp = np.sum((predictions == 1) & (val_labels == 1))
        
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        # Select most aggressive threshold with FPR ≤ target_fpr
        if fpr <= target_fpr:
            if best_theta is None or theta > best_theta:
                best_theta = theta
                best_percentile = percentile
                best_fpr = fpr
    
    # Fallback: if no threshold meets target, use lowest-FPR threshold
    if best_theta is None:
        log(f"[Magic Validation] WARNING: No threshold achieves FPR ≤ {target_fpr:.1%}")
        log(f"[Magic Validation] Using threshold with lowest FPR as fallback")
        
        fprs = []
        for theta in candidate_thresholds:
            predictions = (val_scores > theta).astype(int)
            tn = np.sum((predictions == 0) & (val_labels == 0))
            fp = np.sum((predictions == 1) & (val_labels == 0))
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            fprs.append(fpr)
        
        min_fpr_idx = np.argmin(fprs)
        best_theta = candidate_thresholds[min_fpr_idx]
        best_percentile = percentiles[min_fpr_idx]
        best_fpr = fprs[min_fpr_idx]
    
    log(f"[Magic Validation] θ = {best_theta:.6f} (percentile={best_percentile:.1f}, FPR={best_fpr:.1%})")
    
    return {
        "theta": best_theta,
        "percentile": best_percentile,
        "val_fpr": best_fpr
    }


def apply_threshold_to_test(
    test_scores: np.ndarray,
    theta: float
) -> np.ndarray:
    """
    Apply threshold to test scores.
    
    Args:
        test_scores: Test outlier scores
        theta: Threshold from validation
    
    Returns:
        Binary predictions [num_test_nodes]
    """
    predictions = (test_scores > theta).astype(int)
    
    flagged_count = np.sum(predictions)
    log(f"[Magic Test] Flagged {flagged_count}/{len(predictions)} nodes as malicious")
    
    return predictions


def load_embeddings_from_csv(csv_dir: str, embedding_col_prefix: str = "emb_") -> Tuple[np.ndarray, List[int]]:
    """
    Load node embeddings from CSV files (if saved during inference).
    
    Args:
        csv_dir: Directory containing CSV files with embeddings
        embedding_col_prefix: Prefix for embedding columns
    
    Returns:
        Tuple of (embeddings array, node_ids)
    """
    files = sorted([os.path.join(csv_dir, f) for f in listdir_sorted(csv_dir)])
    
    all_embeddings = []
    all_node_ids = []
    
    for file in files:
        df = pd.read_csv(file)
        
        # Extract embedding columns
        emb_cols = [col for col in df.columns if col.startswith(embedding_col_prefix)]
        
        if len(emb_cols) == 0:
            raise ValueError(f"No embedding columns found in {file} with prefix '{embedding_col_prefix}'")
        
        embeddings = df[emb_cols].values
        # Handle both 'node_id' and 'node' column names
        if "node_id" in df.columns:
            node_ids = df["node_id"].values.tolist()
        elif "node" in df.columns:
            node_ids = df["node"].values.tolist()
        else:
            node_ids = list(range(len(df)))
        
        all_embeddings.append(embeddings)
        all_node_ids.extend(node_ids)
    
    all_embeddings = np.vstack(all_embeddings)
    
    log(f"[Magic] Loaded {len(all_embeddings)} node embeddings from {len(files)} files")
    
    return all_embeddings, all_node_ids


def process_magic_knn_detection(
    val_tw_path: str,
    test_tw_path: str,
    val_labels: np.ndarray,
    test_labels: np.ndarray,
    knn_k: int = 20,
    target_fpr: float = 0.01,
    embedding_col_prefix: str = "emb_"
) -> Dict:
    """
    Full MAGIC KNN detection pipeline.
    
    Args:
        val_tw_path: Path to validation CSV files (with embeddings or scores)
        test_tw_path: Path to test CSV files
        val_labels: Validation ground truth labels
        test_labels: Test ground truth labels
        knn_k: Number of nearest neighbors (default: 20)
        target_fpr: Target FPR for threshold selection (default: 0.01)
        embedding_col_prefix: Prefix for embedding columns in CSV
    
    Returns:
        Dictionary with detection results: theta, predictions, scores
    """
    log(f"\n{'='*60}")
    log("MAGIC KNN Detection Pipeline")
    log(f"{'='*60}")
    
    # Step 1: Load or extract embeddings (validation)
    log("\n[Step 1/5] Loading validation embeddings...")
    try:
        val_embeddings, val_node_ids = load_embeddings_from_csv(val_tw_path, embedding_col_prefix)
    except Exception as e:
        log(f"Warning: Could not load embeddings from CSV: {e}")
        log("Attempting to use pre-computed 'magic_score' column instead...")
        
        # Fallback: load magic_score directly if embeddings not available
        val_scores = load_magic_scores_from_csv(val_tw_path)
        test_scores = load_magic_scores_from_csv(test_tw_path)
        
        # Step 2: Select θ from validation
        log("\n[Step 2/5] Selecting threshold θ from validation...")
        result = sweep_validation_threshold(val_scores, val_labels, target_fpr)
        theta = result["theta"]
        
        # Step 3: Apply to test
        log("\n[Step 3/5] Applying threshold to test data...")
        predictions = apply_threshold_to_test(test_scores, theta)
        
        log(f"\n{'='*60}")
        log(f"MAGIC KNN Detection Complete")
        log(f"  θ threshold: {theta:.6f}")
        log(f"  Flagged nodes: {np.sum(predictions)}/{len(predictions)}")
        log(f"{'='*60}\n")
        
        return {
            "theta": theta,
            "percentile": result["percentile"],
            "val_fpr": result["val_fpr"],
            "predictions": predictions,
            "test_scores": test_scores,
            "val_scores": val_scores
        }
    
    # Step 2: Build KNN index on validation
    log("\n[Step 2/5] Building KNN index on validation embeddings...")
    knn_index = build_knn_index(val_embeddings, k=knn_k)
    
    # Step 3: Compute outlier scores for validation
    log("\n[Step 3/5] Computing validation outlier scores...")
    val_scores = compute_knn_outlier_scores(val_embeddings, knn_index)
    log(f"  Validation score range: [{np.min(val_scores):.6f}, {np.max(val_scores):.6f}]")
    
    # Step 4: Select θ from validation
    log("\n[Step 4/5] Selecting threshold θ from validation...")
    result = sweep_validation_threshold(val_scores, val_labels, target_fpr)
    theta = result["theta"]
    
    # Step 5: Load test embeddings and compute scores
    log("\n[Step 5/5] Computing test outlier scores...")
    test_embeddings, test_node_ids = load_embeddings_from_csv(test_tw_path, embedding_col_prefix)
    test_scores = compute_knn_outlier_scores(test_embeddings, knn_index)
    log(f"  Test score range: [{np.min(test_scores):.6f}, {np.max(test_scores):.6f}]")
    
    # Apply threshold
    predictions = apply_threshold_to_test(test_scores, theta)
    
    log(f"\n{'='*60}")
    log(f"MAGIC KNN Detection Complete")
    log(f"  θ threshold: {theta:.6f}")
    log(f"  Flagged nodes: {np.sum(predictions)}/{len(predictions)}")
    log(f"{'='*60}\n")
    
    return {
        "theta": theta,
        "percentile": result["percentile"],
        "val_fpr": result["val_fpr"],
        "predictions": predictions,
        "test_scores": test_scores,
        "val_scores": val_scores,
        "knn_index": knn_index
    }


def load_magic_scores_from_csv(csv_dir: str) -> np.ndarray:
    """
    Load pre-computed magic_score or loss from CSV files.
    
    Args:
        csv_dir: Directory containing CSV files with magic_score or loss column
    
    Returns:
        Array of scores
    """
    files = sorted([os.path.join(csv_dir, f) for f in listdir_sorted(csv_dir)])
    
    all_scores = []
    
    for file in files:
        df = pd.read_csv(file)
        
        # Try magic_score first, fall back to loss
        if "magic_score" in df.columns:
            scores = df["magic_score"].values
        elif "loss" in df.columns:
            log(f"[Magic] Using 'loss' column as fallback for magic_score in {os.path.basename(file)}")
            scores = df["loss"].values
        else:
            raise ValueError(f"No 'magic_score' or 'loss' column found in {file}")
        
        all_scores.append(scores)
    
    all_scores = np.concatenate(all_scores)
    
    log(f"[Magic] Loaded {len(all_scores)} scores from {len(files)} files")
    
    return all_scores
