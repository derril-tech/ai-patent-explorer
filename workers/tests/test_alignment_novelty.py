import pytest
import numpy as np
from typing import List, Dict, Any, Tuple
from unittest.mock import Mock, patch

# Import the workers we want to test
from src.workers.align_worker.worker import AlignWorker
from src.workers.novelty_worker.worker import NoveltyWorker


def calculate_brier_score(probabilities: List[float], actual_outcomes: List[int]) -> float:
    """Calculate Brier score for probabilistic predictions."""
    if len(probabilities) != len(actual_outcomes):
        raise ValueError("Probabilities and outcomes must have same length")
    
    squared_errors = [(p - a) ** 2 for p, a in zip(probabilities, actual_outcomes)]
    return np.mean(squared_errors)


def calculate_overlap_accuracy(
    predicted_overlaps: List[Dict[str, Any]], 
    human_labels: List[Dict[str, Any]]
) -> Dict[str, float]:
    """Calculate accuracy metrics for overlap detection."""
    if len(predicted_overlaps) != len(human_labels):
        raise ValueError("Predictions and labels must have same length")
    
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0
    
    for pred, label in zip(predicted_overlaps, human_labels):
        pred_has_overlap = pred.get('has_overlap', False)
        label_has_overlap = label.get('has_overlap', False)
        
        if pred_has_overlap and label_has_overlap:
            true_positives += 1
        elif pred_has_overlap and not label_has_overlap:
            false_positives += 1
        elif not pred_has_overlap and label_has_overlap:
            false_negatives += 1
        else:
            true_negatives += 1
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (true_positives + true_negatives) / len(predicted_overlaps)
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'accuracy': accuracy
    }


def calculate_gap_accuracy(
    predicted_gaps: List[Dict[str, Any]], 
    human_labels: List[Dict[str, Any]]
) -> Dict[str, float]:
    """Calculate accuracy metrics for gap detection."""
    if len(predicted_gaps) != len(human_labels):
        raise ValueError("Predictions and labels must have same length")
    
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0
    
    for pred, label in zip(predicted_gaps, human_labels):
        pred_has_gap = pred.get('has_gap', False)
        label_has_gap = label.get('has_gap', False)
        
        if pred_has_gap and label_has_gap:
            true_positives += 1
        elif pred_has_gap and not label_has_gap:
            false_positives += 1
        elif not pred_has_gap and label_has_gap:
            false_negatives += 1
        else:
            true_negatives += 1
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (true_positives + true_negatives) / len(predicted_gaps)
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'accuracy': accuracy
    }


def evaluate_alignment_system(
    align_worker: AlignWorker,
    test_cases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Evaluate alignment system performance."""
    results = {
        'overlap_metrics': [],
        'gap_metrics': [],
        'similarity_correlation': [],
        'alignment_type_accuracy': []
    }
    
    for test_case in test_cases:
        target_claim = test_case['target_claim']
        reference_claims = test_case['reference_claims']
        human_labels = test_case['human_labels']
        
        # Get alignments from worker
        alignments = align_worker.align_claim_clauses(target_claim, reference_claims)
        
        # Evaluate overlap detection
        predicted_overlaps = [
            {'has_overlap': align['similarity_score'] > 0.7} 
            for align in alignments
        ]
        
        overlap_metrics = calculate_overlap_accuracy(predicted_overlaps, human_labels)
        results['overlap_metrics'].append(overlap_metrics)
        
        # Evaluate gap detection
        predicted_gaps = [
            {'has_gap': align['similarity_score'] < 0.3} 
            for align in alignments
        ]
        
        gap_metrics = calculate_gap_accuracy(predicted_gaps, human_labels)
        results['gap_metrics'].append(gap_metrics)
        
        # Calculate similarity correlation
        predicted_similarities = [align['similarity_score'] for align in alignments]
        human_similarities = [label.get('similarity_score', 0) for label in human_labels]
        
        if len(predicted_similarities) == len(human_similarities) and len(predicted_similarities) > 1:
            correlation = np.corrcoef(predicted_similarities, human_similarities)[0, 1]
            if not np.isnan(correlation):
                results['similarity_correlation'].append(correlation)
        
        # Evaluate alignment type accuracy
        correct_types = 0
        total_types = 0
        
        for align, label in zip(alignments, human_labels):
            if 'alignment_type' in label:
                total_types += 1
                if align['alignment_type'] == label['alignment_type']:
                    correct_types += 1
        
        if total_types > 0:
            type_accuracy = correct_types / total_types
            results['alignment_type_accuracy'].append(type_accuracy)
    
    # Aggregate results
    aggregated_results = {
        'overlap_precision': np.mean([m['precision'] for m in results['overlap_metrics']]),
        'overlap_recall': np.mean([m['recall'] for m in results['overlap_metrics']]),
        'overlap_f1': np.mean([m['f1_score'] for m in results['overlap_metrics']]),
        'gap_precision': np.mean([m['precision'] for m in results['gap_metrics']]),
        'gap_recall': np.mean([m['recall'] for m in results['gap_metrics']]),
        'gap_f1': np.mean([m['f1_score'] for m in results['gap_metrics']]),
        'similarity_correlation': np.mean(results['similarity_correlation']) if results['similarity_correlation'] else 0,
        'alignment_type_accuracy': np.mean(results['alignment_type_accuracy']) if results['alignment_type_accuracy'] else 0
    }
    
    return aggregated_results


def evaluate_novelty_system(
    novelty_worker: NoveltyWorker,
    test_cases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Evaluate novelty system performance."""
    results = {
        'novelty_brier_scores': [],
        'obviousness_brier_scores': [],
        'confidence_calibration': [],
        'clause_level_accuracy': []
    }
    
    for test_case in test_cases:
        patent_id = test_case['patent_id']
        claim_num = test_case['claim_num']
        human_labels = test_case['human_labels']
        
        # Get novelty scores from worker
        novelty_results = novelty_worker.calculate_novelty_scores(patent_id, claim_num)
        
        # Calculate Brier scores for novelty
        predicted_novelty = novelty_results['claim_novelty_score']
        actual_novelty = human_labels.get('novelty_label', 0.5)  # 0=not novel, 1=novel
        
        novelty_brier = calculate_brier_score([predicted_novelty], [actual_novelty])
        results['novelty_brier_scores'].append(novelty_brier)
        
        # Calculate Brier scores for obviousness
        predicted_obviousness = novelty_results['obviousness_score']
        actual_obviousness = human_labels.get('obviousness_label', 0.5)  # 0=not obvious, 1=obvious
        
        obviousness_brier = calculate_brier_score([predicted_obviousness], [actual_obviousness])
        results['obviousness_brier_scores'].append(obviousness_brier)
        
        # Evaluate confidence calibration
        confidence_band = novelty_results['calibrated_scores']['confidence_band']
        human_confidence = human_labels.get('confidence_label', 'medium')
        
        confidence_correct = (confidence_band == human_confidence)
        results['confidence_calibration'].append(confidence_correct)
        
        # Evaluate clause-level accuracy
        clause_predictions = novelty_results['clause_novelty_scores']
        clause_labels = human_labels.get('clause_labels', [])
        
        if len(clause_predictions) == len(clause_labels):
            clause_correct = 0
            total_clauses = 0
            
            for pred, label in zip(clause_predictions, clause_labels):
                total_clauses += 1
                pred_novel = pred['novelty_score'] > 0.5
                label_novel = label.get('is_novel', False)
                
                if pred_novel == label_novel:
                    clause_correct += 1
            
            if total_clauses > 0:
                clause_accuracy = clause_correct / total_clauses
                results['clause_level_accuracy'].append(clause_accuracy)
    
    # Aggregate results
    aggregated_results = {
        'novelty_brier_score': np.mean(results['novelty_brier_scores']),
        'obviousness_brier_score': np.mean(results['obviousness_brier_scores']),
        'confidence_accuracy': np.mean(results['confidence_calibration']),
        'clause_accuracy': np.mean(results['clause_level_accuracy']) if results['clause_level_accuracy'] else 0
    }
    
    return aggregated_results


class TestAlignmentEvaluation:
    """Test cases for alignment evaluation."""
    
    def test_overlap_detection_accuracy(self):
        """Test overlap detection accuracy."""
        # Mock test data
        test_cases = [
            {
                'target_claim': {
                    'id': 'claim1',
                    'text': 'A method for processing data comprising: receiving input data; analyzing the data; outputting results.'
                },
                'reference_claims': [
                    {
                        'id': 'ref1',
                        'text': 'A method for processing data comprising: receiving input data; analyzing the data; outputting results.'
                    },
                    {
                        'id': 'ref2', 
                        'text': 'A system for data processing comprising: a processor; a memory; an output device.'
                    }
                ],
                'human_labels': [
                    {'has_overlap': True, 'similarity_score': 0.9, 'alignment_type': 'exact_match'},
                    {'has_overlap': False, 'similarity_score': 0.2, 'alignment_type': 'no_match'}
                ]
            }
        ]
        
        # Mock align worker
        align_worker = Mock()
        align_worker.align_claim_clauses.return_value = [
            {'similarity_score': 0.9, 'alignment_type': 'exact_match'},
            {'similarity_score': 0.2, 'alignment_type': 'no_match'}
        ]
        
        results = evaluate_alignment_system(align_worker, test_cases)
        
        assert results['overlap_precision'] == 1.0
        assert results['overlap_recall'] == 1.0
        assert results['overlap_f1'] == 1.0
        assert results['gap_precision'] == 1.0
        assert results['gap_recall'] == 1.0
        assert results['gap_f1'] == 1.0
        assert results['alignment_type_accuracy'] == 1.0
    
    def test_similarity_correlation(self):
        """Test similarity score correlation with human judgments."""
        test_cases = [
            {
                'target_claim': {'id': 'claim1', 'text': 'Test claim'},
                'reference_claims': [{'id': 'ref1', 'text': 'Reference claim'}],
                'human_labels': [{'similarity_score': 0.8}]
            }
        ]
        
        align_worker = Mock()
        align_worker.align_claim_clauses.return_value = [
            {'similarity_score': 0.8, 'alignment_type': 'high_similarity'}
        ]
        
        results = evaluate_alignment_system(align_worker, test_cases)
        
        assert results['similarity_correlation'] == 1.0
    
    def test_empty_test_cases(self):
        """Test handling of empty test cases."""
        align_worker = Mock()
        results = evaluate_alignment_system(align_worker, [])
        
        assert results['overlap_precision'] == 0
        assert results['overlap_recall'] == 0
        assert results['overlap_f1'] == 0


class TestNoveltyEvaluation:
    """Test cases for novelty evaluation."""
    
    def test_novelty_brier_score(self):
        """Test novelty Brier score calculation."""
        test_cases = [
            {
                'patent_id': 'patent1',
                'claim_num': 1,
                'human_labels': {
                    'novelty_label': 1,  # Novel
                    'obviousness_label': 0,  # Not obvious
                    'confidence_label': 'high',
                    'clause_labels': [
                        {'is_novel': True},
                        {'is_novel': False}
                    ]
                }
            }
        ]
        
        novelty_worker = Mock()
        novelty_worker.calculate_novelty_scores.return_value = {
            'claim_novelty_score': 0.9,
            'obviousness_score': 0.1,
            'calibrated_scores': {'confidence_band': 'high'},
            'clause_novelty_scores': [
                {'novelty_score': 0.8},
                {'novelty_score': 0.3}
            ]
        }
        
        results = evaluate_novelty_system(novelty_worker, test_cases)
        
        # Brier score should be low for good predictions
        assert results['novelty_brier_score'] < 0.1
        assert results['obviousness_brier_score'] < 0.1
        assert results['confidence_accuracy'] == 1.0
        assert results['clause_accuracy'] == 1.0
    
    def test_brier_score_calculation(self):
        """Test Brier score calculation."""
        probabilities = [0.8, 0.2, 0.9]
        outcomes = [1, 0, 1]
        
        brier_score = calculate_brier_score(probabilities, outcomes)
        
        # Expected: ((0.8-1)² + (0.2-0)² + (0.9-1)²) / 3 = (0.04 + 0.04 + 0.01) / 3 = 0.03
        expected = (0.04 + 0.04 + 0.01) / 3
        assert abs(brier_score - expected) < 0.001
    
    def test_overlap_accuracy_calculation(self):
        """Test overlap accuracy calculation."""
        predicted_overlaps = [
            {'has_overlap': True},
            {'has_overlap': False},
            {'has_overlap': True},
            {'has_overlap': False}
        ]
        
        human_labels = [
            {'has_overlap': True},
            {'has_overlap': False},
            {'has_overlap': False},  # False positive
            {'has_overlap': True}    # False negative
        ]
        
        metrics = calculate_overlap_accuracy(predicted_overlaps, human_labels)
        
        # TP=1, FP=1, FN=1, TN=1
        assert metrics['precision'] == 0.5  # 1/(1+1)
        assert metrics['recall'] == 0.5     # 1/(1+1)
        assert metrics['f1_score'] == 0.5   # 2*(0.5*0.5)/(0.5+0.5)
        assert metrics['accuracy'] == 0.5   # (1+1)/4
    
    def test_empty_predictions(self):
        """Test handling of empty predictions."""
        novelty_worker = Mock()
        results = evaluate_novelty_system(novelty_worker, [])
        
        assert results['novelty_brier_score'] == 0
        assert results['obviousness_brier_score'] == 0
        assert results['confidence_accuracy'] == 0
        assert results['clause_accuracy'] == 0


class TestIntegrationEvaluation:
    """Integration tests for alignment and novelty evaluation."""
    
    @patch('src.workers.align_worker.worker.AlignWorker')
    @patch('src.workers.novelty_worker.worker.NoveltyWorker')
    def test_end_to_end_evaluation(self, mock_novelty_worker, mock_align_worker):
        """Test end-to-end evaluation pipeline."""
        # Setup mock workers
        align_worker = mock_align_worker.return_value
        novelty_worker = mock_novelty_worker.return_value
        
        # Mock alignment results
        align_worker.align_claim_clauses.return_value = [
            {'similarity_score': 0.8, 'alignment_type': 'high_similarity'},
            {'similarity_score': 0.3, 'alignment_type': 'low_similarity'}
        ]
        
        # Mock novelty results
        novelty_worker.calculate_novelty_scores.return_value = {
            'claim_novelty_score': 0.7,
            'obviousness_score': 0.3,
            'calibrated_scores': {'confidence_band': 'high'},
            'clause_novelty_scores': [
                {'novelty_score': 0.8},
                {'novelty_score': 0.6}
            ]
        }
        
        # Test cases
        alignment_test_cases = [
            {
                'target_claim': {'id': 'claim1', 'text': 'Test claim'},
                'reference_claims': [{'id': 'ref1', 'text': 'Reference claim'}],
                'human_labels': [{'has_overlap': True, 'similarity_score': 0.8}]
            }
        ]
        
        novelty_test_cases = [
            {
                'patent_id': 'patent1',
                'claim_num': 1,
                'human_labels': {
                    'novelty_label': 1,
                    'obviousness_label': 0,
                    'confidence_label': 'high',
                    'clause_labels': [{'is_novel': True}, {'is_novel': True}]
                }
            }
        ]
        
        # Run evaluations
        alignment_results = evaluate_alignment_system(align_worker, alignment_test_cases)
        novelty_results = evaluate_novelty_system(novelty_worker, novelty_test_cases)
        
        # Verify results
        assert alignment_results['overlap_precision'] > 0
        assert novelty_results['novelty_brier_score'] < 0.5  # Reasonable Brier score
        assert novelty_results['confidence_accuracy'] > 0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
