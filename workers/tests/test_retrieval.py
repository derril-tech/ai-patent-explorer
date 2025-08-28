import pytest
import numpy as np
from typing import List, Dict, Any

def calculate_recall_at_k(relevant_docs: List[str], retrieved_docs: List[str], k: int) -> float:
    """Calculate recall@k for retrieval evaluation."""
    if not relevant_docs:
        return 0.0
    
    # Get top k retrieved documents
    top_k_retrieved = retrieved_docs[:k]
    
    # Count how many relevant documents are in top k
    relevant_in_top_k = len(set(relevant_docs) & set(top_k_retrieved))
    
    return relevant_in_top_k / len(relevant_docs)

def calculate_mrr(relevant_docs: List[str], retrieved_docs: List[str]) -> float:
    """Calculate Mean Reciprocal Rank (MRR) for retrieval evaluation."""
    if not relevant_docs:
        return 0.0
    
    reciprocal_ranks = []
    
    for relevant_doc in relevant_docs:
        if relevant_doc in retrieved_docs:
            rank = retrieved_docs.index(relevant_doc) + 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            # If relevant document is not retrieved, add 0
            reciprocal_ranks.append(0.0)
    
    return np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0

def calculate_precision_at_k(relevant_docs: List[str], retrieved_docs: List[str], k: int) -> float:
    """Calculate precision@k for retrieval evaluation."""
    if k == 0:
        return 0.0
    
    # Get top k retrieved documents
    top_k_retrieved = retrieved_docs[:k]
    
    # Count how many relevant documents are in top k
    relevant_in_top_k = len(set(relevant_docs) & set(top_k_retrieved))
    
    return relevant_in_top_k / k

def evaluate_retrieval_system(
    queries: List[Dict[str, Any]],
    retrieval_results: List[List[str]],
    ground_truth: List[List[str]]
) -> Dict[str, float]:
    """Evaluate retrieval system performance."""
    
    assert len(queries) == len(retrieval_results) == len(ground_truth), "All lists must have same length"
    
    # Calculate metrics for each query
    recall_at_10_scores = []
    recall_at_20_scores = []
    mrr_scores = []
    precision_at_10_scores = []
    
    for i, (query, retrieved, relevant) in enumerate(zip(queries, retrieval_results, ground_truth)):
        # Calculate recall@10
        recall_10 = calculate_recall_at_k(relevant, retrieved, 10)
        recall_at_10_scores.append(recall_10)
        
        # Calculate recall@20
        recall_20 = calculate_recall_at_k(relevant, retrieved, 20)
        recall_at_20_scores.append(recall_20)
        
        # Calculate MRR
        mrr = calculate_mrr(relevant, retrieved)
        mrr_scores.append(mrr)
        
        # Calculate precision@10
        precision_10 = calculate_precision_at_k(relevant, retrieved, 10)
        precision_at_10_scores.append(precision_10)
    
    # Calculate average metrics
    results = {
        'recall@10': np.mean(recall_at_10_scores),
        'recall@20': np.mean(recall_at_20_scores),
        'mrr': np.mean(mrr_scores),
        'precision@10': np.mean(precision_at_10_scores),
        'num_queries': len(queries)
    }
    
    return results

# Test cases
class TestRetrievalEvaluation:
    
    def test_recall_at_k(self):
        """Test recall@k calculation."""
        relevant = ['doc1', 'doc2', 'doc3']
        retrieved = ['doc1', 'doc4', 'doc2', 'doc5', 'doc3']
        
        # Test recall@3
        recall_3 = calculate_recall_at_k(relevant, retrieved, 3)
        assert recall_3 == 2/3  # 2 relevant docs in top 3
        
        # Test recall@5
        recall_5 = calculate_recall_at_k(relevant, retrieved, 5)
        assert recall_5 == 1.0  # All relevant docs in top 5
    
    def test_mrr(self):
        """Test MRR calculation."""
        relevant = ['doc1', 'doc2']
        retrieved = ['doc3', 'doc1', 'doc4', 'doc2']
        
        mrr = calculate_mrr(relevant, retrieved)
        # doc1 is at rank 2 (1/2), doc2 is at rank 4 (1/4)
        expected_mrr = (1/2 + 1/4) / 2
        assert mrr == expected_mrr
    
    def test_precision_at_k(self):
        """Test precision@k calculation."""
        relevant = ['doc1', 'doc2', 'doc3']
        retrieved = ['doc1', 'doc4', 'doc2', 'doc5', 'doc3']
        
        # Test precision@3
        precision_3 = calculate_precision_at_k(relevant, retrieved, 3)
        assert precision_3 == 2/3  # 2 relevant docs out of 3 retrieved
    
    def test_evaluate_retrieval_system(self):
        """Test full retrieval system evaluation."""
        queries = [
            {'id': 'q1', 'text': 'machine learning algorithm'},
            {'id': 'q2', 'text': 'neural network architecture'}
        ]
        
        retrieval_results = [
            ['doc1', 'doc2', 'doc3', 'doc4', 'doc5'],
            ['doc2', 'doc4', 'doc1', 'doc6', 'doc7']
        ]
        
        ground_truth = [
            ['doc1', 'doc3', 'doc5'],
            ['doc2', 'doc4', 'doc6']
        ]
        
        results = evaluate_retrieval_system(queries, retrieval_results, ground_truth)
        
        assert 'recall@10' in results
        assert 'recall@20' in results
        assert 'mrr' in results
        assert 'precision@10' in results
        assert 'num_queries' in results
        assert results['num_queries'] == 2

if __name__ == "__main__":
    # Run a simple evaluation example
    print("Running retrieval evaluation test...")
    
    # Mock data
    queries = [
        {'id': 'q1', 'text': 'machine learning'},
        {'id': 'q2', 'text': 'neural networks'},
        {'id': 'q3', 'text': 'deep learning'}
    ]
    
    retrieval_results = [
        ['doc1', 'doc2', 'doc3', 'doc4', 'doc5'],
        ['doc2', 'doc4', 'doc1', 'doc6', 'doc7'],
        ['doc3', 'doc1', 'doc5', 'doc8', 'doc9']
    ]
    
    ground_truth = [
        ['doc1', 'doc3'],
        ['doc2', 'doc4'],
        ['doc3', 'doc5']
    ]
    
    results = evaluate_retrieval_system(queries, retrieval_results, ground_truth)
    
    print("Retrieval Evaluation Results:")
    for metric, value in results.items():
        print(f"{metric}: {value:.4f}")
