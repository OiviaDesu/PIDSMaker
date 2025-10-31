"""
MAGIC Adaptation Mechanism Implementation
Paper: MAGIC §4.4, §6.3
https://www.usenix.org/conference/usenixsecurity24/presentation/jia

Implements periodic model adaptation to reduce false positives over time.
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional
from sklearn.neighbors import NearestNeighbors
from pidsmaker.utils.utils import log


class MagicAdaptationManager:
    """
    Manages MAGIC adaptation: feedback collection, KNN store updates, and periodic fine-tuning.
    Paper: MAGIC §4.4, §6.3
    """
    
    def __init__(
        self,
        initial_knn_index: NearestNeighbors,
        initial_embeddings: np.ndarray,
        knn_k: int = 20,
        max_store_size: int = 10000,
        feedback_budget: float = 0.15,
        finetune_epochs: int = 5,
        finetune_lr: float = 1e-5,
        device: str = 'cpu'
    ):
        """
        Initialize adaptation manager.
        
        Args:
            initial_knn_index: Initial KNN index from validation
            initial_embeddings: Initial embeddings from validation
            knn_k: Number of nearest neighbors
            max_store_size: Maximum KNN store size (default: 10000)
            feedback_budget: Fraction of FPs to collect feedback on (default: 0.15 = 15%)
            finetune_epochs: Epochs for periodic fine-tuning (default: 5)
            finetune_lr: Learning rate for fine-tuning (default: 1e-5)
            device: Device for training
        """
        self.knn_index = initial_knn_index
        self.knn_embeddings = initial_embeddings
        self.knn_k = knn_k
        self.max_store_size = max_store_size
        self.feedback_budget = feedback_budget
        self.finetune_epochs = finetune_epochs
        self.finetune_lr = finetune_lr
        self.device = device
        
        # Track adaptation history
        self.adaptation_history = []
        self.feedback_count = 0
        
        log(f"[Magic Adaptation] Initialized with store_size={len(initial_embeddings)}, "
            f"budget={feedback_budget:.1%}, max_size={max_store_size}")
    
    def collect_feedback(
        self,
        predictions: np.ndarray,
        scores: np.ndarray,
        embeddings: np.ndarray,
        labels: np.ndarray,
        strategy: str = 'top_scores_recent'
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Collect analyst feedback on false positives.
        Paper: MAGIC §4.4 - Analyst feedback on top-K% FPs
        
        Args:
            predictions: Binary predictions [num_nodes]
            scores: Outlier scores [num_nodes]
            embeddings: Node embeddings [num_nodes, emb_dim]
            labels: Ground truth labels [num_nodes]
            strategy: Feedback collection strategy ('top_scores_recent')
        
        Returns:
            Tuple of (feedback_embeddings, feedback_labels) for confirmed benign nodes
        """
        # Identify false positives
        fp_mask = (predictions == 1) & (labels == 0)
        fp_indices = np.where(fp_mask)[0]
        
        if len(fp_indices) == 0:
            log("[Magic Feedback] No false positives to collect feedback on")
            return np.array([]), np.array([])
        
        # Select top-K% by score
        num_feedback = max(1, int(len(fp_indices) * self.feedback_budget))
        
        if strategy == 'top_scores_recent':
            # Sort FPs by score (descending) and take top-K%
            fp_scores = scores[fp_indices]
            top_indices = np.argsort(fp_scores)[::-1][:num_feedback]
            selected_fp_indices = fp_indices[top_indices]
        else:
            # Random sampling
            selected_fp_indices = np.random.choice(fp_indices, num_feedback, replace=False)
        
        feedback_embeddings = embeddings[selected_fp_indices]
        feedback_labels = labels[selected_fp_indices]  # Should all be 0 (benign)
        
        self.feedback_count += len(selected_fp_indices)
        
        log(f"[Magic Feedback] Collected {len(selected_fp_indices)} FP samples "
            f"({len(selected_fp_indices)/len(fp_indices):.1%} of {len(fp_indices)} FPs)")
        
        return feedback_embeddings, feedback_labels
    
    def update_knn_store(
        self,
        new_benign_embeddings: np.ndarray,
        discard_oldest: bool = True
    ):
        """
        Update KNN store with confirmed benign nodes, applying discounting if needed.
        Paper: MAGIC §4.4 - Update KNN detector memory with benign feedback, discard oldest
        
        Args:
            new_benign_embeddings: New confirmed benign node embeddings
            discard_oldest: Whether to discard oldest entries if max_store_size exceeded
        """
        if len(new_benign_embeddings) == 0:
            return
        
        # Add new benign embeddings
        self.knn_embeddings = np.vstack([self.knn_embeddings, new_benign_embeddings])
        
        # Apply discounting if store exceeds max size
        if discard_oldest and len(self.knn_embeddings) > self.max_store_size:
            # Remove oldest entries (FIFO)
            num_to_discard = len(self.knn_embeddings) - self.max_store_size
            self.knn_embeddings = self.knn_embeddings[num_to_discard:]
            
            log(f"[Magic KNN Store] Discarded {num_to_discard} oldest entries (FIFO)")
        
        # Rebuild KNN index
        self.knn_index = NearestNeighbors(
            n_neighbors=min(self.knn_k, len(self.knn_embeddings)),
            algorithm='ball_tree',
            metric='euclidean'
        )
        self.knn_index.fit(self.knn_embeddings)
        
        log(f"[Magic KNN Store] Updated: {len(self.knn_embeddings)} total embeddings "
            f"(added {len(new_benign_embeddings)})")
    
    def finetune_encoder(
        self,
        model: nn.Module,
        benign_graphs: List,
        optimizer_class=torch.optim.Adam
    ):
        """
        Periodically fine-tune encoder on confirmed benign graphs.
        Paper: MAGIC §6.3 - Periodic fine-tuning with analyst feedback
        
        Args:
            model: MAGIC model with encoder
            benign_graphs: List of confirmed benign graph batches
            optimizer_class: Optimizer class (default: Adam)
        """
        if len(benign_graphs) == 0:
            log("[Magic Fine-tune] No benign graphs to fine-tune on")
            return
        
        model.train()
        optimizer = optimizer_class(model.parameters(), lr=self.finetune_lr)
        
        log(f"[Magic Fine-tune] Fine-tuning encoder for {self.finetune_epochs} epochs "
            f"on {len(benign_graphs)} benign graphs (lr={self.finetune_lr})")
        
        for epoch in range(self.finetune_epochs):
            epoch_loss = 0.0
            
            for graph_batch in benign_graphs:
                optimizer.zero_grad()
                
                # Forward pass (reconstruction loss)
                if hasattr(model, 'forward'):
                    output = model(
                        graph_batch.x.to(self.device),
                        graph_batch.edge_index.to(self.device)
                    )
                    
                    # Compute reconstruction loss
                    if isinstance(output, tuple) and len(output) >= 2:
                        # (embeddings, reconstructed_features, ...)
                        reconstructed = output[1]
                        loss = nn.functional.mse_loss(reconstructed, graph_batch.x.to(self.device))
                    else:
                        log("[Magic Fine-tune] Warning: Could not compute reconstruction loss")
                        continue
                    
                    loss.backward()
                    optimizer.step()
                    
                    epoch_loss += loss.item()
            
            avg_loss = epoch_loss / len(benign_graphs) if len(benign_graphs) > 0 else 0.0
            log(f"  Epoch {epoch+1}/{self.finetune_epochs}: loss={avg_loss:.6f}")
        
        model.eval()
        log("[Magic Fine-tune] Fine-tuning complete")
    
    def adapt_per_day(
        self,
        day_predictions: np.ndarray,
        day_scores: np.ndarray,
        day_embeddings: np.ndarray,
        day_labels: np.ndarray,
        model: Optional[nn.Module] = None,
        benign_graphs: Optional[List] = None
    ) -> Dict:
        """
        Perform one adaptation cycle for a single test day.
        Paper: MAGIC §6.3 - Per-day adaptation cycle
        
        Args:
            day_predictions: Predictions for this day
            day_scores: Outlier scores for this day
            day_embeddings: Node embeddings for this day
            day_labels: Ground truth labels for this day
            model: MAGIC model (optional, for fine-tuning)
            benign_graphs: Benign graph batches (optional, for fine-tuning)
        
        Returns:
            Dictionary with adaptation statistics
        """
        log(f"\n[Magic Adaptation] Starting adaptation cycle for day...")
        
        # Step 1: Collect feedback on FPs
        feedback_embeddings, feedback_labels = self.collect_feedback(
            day_predictions, day_scores, day_embeddings, day_labels
        )
        
        # Step 2: Update KNN store
        if len(feedback_embeddings) > 0:
            self.update_knn_store(feedback_embeddings, discard_oldest=True)
        
        # Step 3: Optionally fine-tune encoder
        if model is not None and benign_graphs is not None and len(benign_graphs) > 0:
            self.finetune_encoder(model, benign_graphs)
        
        # Track history
        fp_count = np.sum((day_predictions == 1) & (day_labels == 0))
        tp_count = np.sum((day_predictions == 1) & (day_labels == 1))
        
        stats = {
            "feedback_collected": len(feedback_embeddings),
            "knn_store_size": len(self.knn_embeddings),
            "fp_count": fp_count,
            "tp_count": tp_count
        }
        
        self.adaptation_history.append(stats)
        
        log(f"[Magic Adaptation] Cycle complete: "
            f"feedback={len(feedback_embeddings)}, "
            f"store_size={len(self.knn_embeddings)}, "
            f"FP={fp_count}, TP={tp_count}")
        
        return stats
    
    def recompute_scores_after_adaptation(
        self,
        embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Recompute outlier scores using updated KNN store.
        
        Args:
            embeddings: Node embeddings to score
        
        Returns:
            Updated outlier scores
        """
        distances, indices = self.knn_index.kneighbors(embeddings)
        scores = np.mean(distances, axis=1)
        
        return scores
    
    def get_adaptation_summary(self) -> Dict:
        """
        Get summary of adaptation history.
        
        Returns:
            Dictionary with adaptation metrics
        """
        if len(self.adaptation_history) == 0:
            return {"cycles": 0}
        
        total_feedback = sum(cycle["feedback_collected"] for cycle in self.adaptation_history)
        final_store_size = self.adaptation_history[-1]["knn_store_size"]
        
        initial_fp = self.adaptation_history[0]["fp_count"]
        final_fp = self.adaptation_history[-1]["fp_count"]
        fp_reduction = (initial_fp - final_fp) / initial_fp if initial_fp > 0 else 0.0
        
        return {
            "cycles": len(self.adaptation_history),
            "total_feedback": total_feedback,
            "final_store_size": final_store_size,
            "initial_fp": initial_fp,
            "final_fp": final_fp,
            "fp_reduction": fp_reduction
        }


def process_magic_adaptive_detection(
    baseline_results: Dict,
    test_days_data: List[Dict],
    model: Optional[nn.Module] = None,
    knn_k: int = 20,
    max_store_size: int = 10000,
    feedback_budget: float = 0.15,
    finetune_epochs: int = 5,
    finetune_lr: float = 1e-5,
    device: str = 'cpu'
) -> Dict:
    """
    Full MAGIC adaptive detection pipeline.
    Paper: MAGIC §6.3
    
    Args:
        baseline_results: Results from baseline detection (theta, knn_index, etc.)
        test_days_data: List of dictionaries per test day with embeddings, labels, graphs
        model: MAGIC model for fine-tuning (optional)
        knn_k: Number of nearest neighbors
        max_store_size: Maximum KNN store size
        feedback_budget: Fraction of FPs for feedback (default: 0.15)
        finetune_epochs: Epochs per fine-tuning cycle
        finetune_lr: Learning rate for fine-tuning
        device: Device for training
    
    Returns:
        Dictionary with adaptive detection results
    """
    log(f"\n{'='*60}")
    log("MAGIC Adaptive Detection Pipeline")
    log(f"{'='*60}")
    
    # Initialize adaptation manager
    manager = MagicAdaptationManager(
        initial_knn_index=baseline_results["knn_index"],
        initial_embeddings=baseline_results["val_embeddings"] if "val_embeddings" in baseline_results else baseline_results["knn_index"]._fit_X,
        knn_k=knn_k,
        max_store_size=max_store_size,
        feedback_budget=feedback_budget,
        finetune_epochs=finetune_epochs,
        finetune_lr=finetune_lr,
        device=device
    )
    
    theta = baseline_results["theta"]
    all_predictions = []
    all_scores = []
    
    # Adapt per day
    for day_idx, day_data in enumerate(test_days_data):
        log(f"\n[Day {day_idx+1}/{len(test_days_data)}] Processing...")
        
        embeddings = day_data["embeddings"]
        labels = day_data["labels"]
        benign_graphs = day_data.get("benign_graphs", None)
        
        # Compute scores with current KNN store
        scores = manager.recompute_scores_after_adaptation(embeddings)
        predictions = (scores > theta).astype(int)
        
        # Perform adaptation
        manager.adapt_per_day(
            predictions, scores, embeddings, labels,
            model=model, benign_graphs=benign_graphs
        )
        
        all_predictions.append(predictions)
        all_scores.append(scores)
    
    # Concatenate results
    all_predictions = np.concatenate(all_predictions)
    all_scores = np.concatenate(all_scores)
    
    # Get adaptation summary
    summary = manager.get_adaptation_summary()
    
    log(f"\n{'='*60}")
    log(f"MAGIC Adaptive Detection Complete")
    log(f"  Adaptation cycles: {summary['cycles']}")
    log(f"  Total feedback: {summary['total_feedback']}")
    log(f"  FP reduction: {summary['fp_reduction']:.1%}")
    log(f"  Initial FP: {summary['initial_fp']}")
    log(f"  Final FP: {summary['final_fp']}")
    log(f"{'='*60}\n")
    
    return {
        "predictions": all_predictions,
        "scores": all_scores,
        "adaptation_summary": summary,
        "adaptation_history": manager.adaptation_history
    }
