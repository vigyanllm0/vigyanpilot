"""
VigyanLLM Protein Structure Prediction - Double Method Approach
Combining Hidden Markov Models and Artificial Neural Networks for enhanced accuracy
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import List, Tuple, Dict, Any
import logging
from dataclasses import dataclass
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class HMMParameters:
    """Hidden Markov Model parameters"""
    N: int  # Number of hidden states (structural features)
    M: int  # Number of observation symbols (amino acids)
    A: np.ndarray  # State transition matrix (N×N)
    B: np.ndarray  # Emission matrix (N×M)
    pi: np.ndarray  # Initial state distribution (N×1)
    
    def __post_init__(self):
        """Validate and normalize parameters"""
        # Ensure rows sum to 1
        self.A = self.A / self.A.sum(axis=1, keepdims=True)
        self.B = self.B / self.B.sum(axis=1, keepdims=True)
        self.pi = self.pi / self.pi.sum()

class ProteinHMM:
    """Hidden Markov Model for protein secondary structure prediction"""
    
    def __init__(self, N_states: int = 5, M_obs: int = 20):
        self.N = N_states  # α-helix, β-sheet, coil, turn, loop
        self.M = M_obs  # 20 standard amino acids
        
        # Initialize parameters
        self.params = self._initialize_parameters()
        
        # Amino acid mapping
        self.aa_to_idx = self._create_aa_mapping()
        
    def _initialize_parameters(self) -> HMMParameters:
        """Initialize HMM parameters with reasonable defaults"""
        # State transition matrix (N×N)
        A = np.random.dirichlet(np.ones(self.N), size=self.N)
        
        # Emission matrix (N×M) - different amino acids prefer different structures
        B = np.random.dirichlet(np.ones(self.M), size=self.N)
        
        # Initial state distribution
        pi = np.random.dirichlet(np.ones(self.N))
        
        return HMMParameters(self.N, self.M, A, B, pi)
    
    def _create_aa_mapping(self) -> Dict[str, int]:
        """Create mapping from amino acid to index"""
        aa_list = ['A', 'R', 'N', 'D', 'C', 'E', 'Q', 'G', 'H', 'I',
                   'L', 'K', 'M', 'F', 'P', 'S', 'T', 'W', 'Y', 'V']
        return {aa: i for i, aa in enumerate(aa_list)}
    
    def sequence_to_indices(self, sequence: str) -> List[int]:
        """Convert amino acid sequence to observation indices"""
        indices = []
        for aa in sequence.upper():
            if aa in self.aa_to_idx:
                indices.append(self.aa_to_idx[aa])
            else:
                # Handle unknown amino acids
                indices.append(0)  # Default to Alanine
        return indices
    
    def viterbi_decode(self, sequence: str) -> Tuple[List[int], float]:
        """Viterbi algorithm for most likely state sequence"""
        obs_seq = self.sequence_to_indices(sequence)
        T = len(obs_seq)
        
        # Initialize DP tables
        delta = np.zeros((T, self.N))
        psi = np.zeros((T, self.N), dtype=int)
        
        # Initialize first column
        delta[0] = self.params.pi * self.params.B[:, obs_seq[0]]
        psi[0] = 0
        
        # Recursion
        for t in range(1, T):
            for j in range(self.N):
                transitions = delta[t-1] * self.params.A[:, j]
                psi[t, j] = np.argmax(transitions)
                delta[t, j] = np.max(transitions) * self.params.B[j, obs_seq[t]]
        
        # Termination
        path_prob = np.max(delta[T-1])
        last_state = np.argmax(delta[T-1])
        
        # Backtrack
        path = [last_state]
        for t in range(T-1, 0, -1):
            path.append(psi[t, path[-1]])
        
        return path[::-1], path_prob
    
    def train_baum_welch(self, sequences: List[str], max_iter: int = 100, tol: float = 1e-6) -> float:
        """Baum-Welch algorithm for HMM training"""
        logger.info("Training HMM on %s sequences", len(sequences))
        
        prev_log_likelihood = -np.inf
        
        for iteration in range(max_iter):
            # E-step: Compute expected counts
            expected_A = np.zeros_like(self.params.A)
            expected_B = np.zeros_like(self.params.B)
            expected_pi = np.zeros_like(self.params.pi)
            total_log_likelihood = 0
            
            for sequence in sequences:
                obs_seq = self.sequence_to_indices(sequence)
                T = len(obs_seq)
                
                # Forward algorithm
                alpha = np.zeros((T, self.N))
                alpha[0] = self.params.pi * self.params.B[:, obs_seq[0]]
                
                for t in range(1, T):
                    for j in range(self.N):
                        alpha[t, j] = np.sum(alpha[t-1] * self.params.A[:, j]) * self.params.B[j, obs_seq[t]]
                
                # Backward algorithm
                beta = np.zeros((T, self.N))
                beta[T-1] = 1.0
                
                for t in range(T-2, -1, -1):
                    for i in range(self.N):
                        beta[t, i] = np.sum(self.params.A[i, :] * self.params.B[:, obs_seq[t+1]] * beta[t+1])
                
                # Compute expected counts
                gamma = alpha * beta
                gamma = gamma / np.sum(gamma, axis=1, keepdims=True)
                
                xi = np.zeros((T-1, self.N, self.N))
                for t in range(T-1):
                    for i in range(self.N):
                        for j in range(self.N):
                            xi[t, i, j] = alpha[t, i] * self.params.A[i, j] * \
                                          self.params.B[j, obs_seq[t+1]] * beta[t+1, j]
                
                # Accumulate expectations
                expected_pi += gamma[0]
                expected_A += np.sum(xi, axis=0)
                
                for j in range(self.N):
                    for k in range(self.M):
                        mask = (obs_seq == k)
                        expected_B[j, k] += np.sum(gamma[mask, j])
                
                total_log_likelihood += np.log(np.sum(alpha[T-1]))
            
            # M-step: Update parameters
            self.params.pi = expected_pi / len(sequences)
            self.params.A = expected_A / np.sum(expected_A, axis=1, keepdims=True)
            self.params.B = expected_B / np.sum(expected_B, axis=1, keepdims=True)
            
            # Check convergence
            if abs(total_log_likelihood - prev_log_likelihood) < tol:
                logger.info("HMM converged after %s iterations", iteration)
                break
            
            prev_log_likelihood = total_log_likelihood
        
        return total_log_likelihood

class ProteinANN(nn.Module):
    """Artificial Neural Network for protein structure prediction"""
    
    def __init__(self, window_size: int = 15, hidden_size: int = 128, 
                 num_classes: int = 5, dropout_rate: float = 0.3):
        super(ProteinANN, self).__init__()
        
        self.window_size = window_size
        self.hidden_size = hidden_size
        self.num_classes = num_classes
        
        # Amino acid embedding layer
        self.embedding = nn.Embedding(20, 32)  # 20 amino acids -> 32D embedding
        
        # Feed-forward layers
        self.fc1 = nn.Linear(window_size * 32, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc3 = nn.Linear(hidden_size // 2, num_classes)
        
        # Dropout for regularization
        self.dropout = nn.Dropout(dropout_rate)
        
        # Activation functions
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=1)
        
    def forward(self, x):
        """Forward pass"""
        # Input shape: (batch_size, sequence_length)
        # Create sliding windows
        windows = self._create_sliding_windows(x)
        
        # Embedding
        embedded = self.embedding(windows)  # (batch_size, window_size, 32)
        embedded = embedded.view(embedded.size(0), -1)  # Flatten
        
        # Feed-forward layers
        out = self.relu(self.fc1(embedded))
        out = self.dropout(out)
        out = self.relu(self.fc2(out))
        out = self.dropout(out)
        out = self.fc3(out)
        
        return self.softmax(out)
    
    def _create_sliding_windows(self, x):
        """Create sliding windows from sequence"""
        batch_size, seq_len = x.size()
        
        # Pad sequence for edge windows
        pad_size = self.window_size // 2
        padded = torch.cat([
            torch.full(batch_size, pad_size, dtype=x.dtype, device=x.device),
            x,
            torch.full(batch_size, pad_size, dtype=x.dtype, device=x.device)
        ], dim=1)
        
        # Create windows
        windows = []
        for i in range(seq_len):
            start = i
            end = i + self.window_size
            windows.append(padded[:, start:end])
        
        return torch.stack(windows, dim=1)  # (batch_size, seq_len, window_size)
    
    def train_steepest_descent(self, train_loader, val_loader, epochs: int = 100, 
                           learning_rate: float = 0.01):
        """Train using steepest descent with overfitting prevention"""
        logger.info("Training ANN with steepest descent for %s epochs", epochs)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.SGD(self.parameters(), lr=learning_rate, momentum=0.9)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=5)
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(epochs):
            # Training phase
            self.train()
            train_loss = 0.0
            
            for batch_idx, (sequences, labels) in enumerate(train_loader):
                optimizer.zero_grad()
                
                outputs = self.forward(sequences)
                loss = criterion(outputs, labels)
                
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            # Validation phase
            self.eval()
            val_loss = 0.0
            
            with torch.no_grad():
                for sequences, labels in val_loader:
                    outputs = self.forward(sequences)
                    loss = criterion(outputs, labels)
                    val_loss += loss.item()
            
            # Learning rate scheduling
            scheduler.step(val_loss)
            
            # Early stopping to prevent overfitting
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model
                torch.save(self.state_dict(), 'best_ann_model.pth')
            else:
                patience_counter += 1
                if patience_counter >= 10:
                    logger.info("Early stopping at epoch %s", epoch)
                    break
            
            if epoch % 10 == 0:
                logger.info("Epoch %s: Train Loss: %s, Val Loss: %s", epoch, train_loss:.4f, val_loss:.4f)

class DoublePredictor:
    """Double prediction method combining HMM and ANN"""
    
    def __init__(self, hmm_states: int = 5, ann_hidden: int = 128):
        self.hmm = ProteinHMM(N_states=hmm_states)
        self.ann = ProteinANN(hidden_size=ann_hidden)
        
        # Structure labels
        self.structure_labels = ['α-helix', 'β-sheet', 'coil', 'turn', 'loop']
        
    def train_double_method(self, sequences: List[str], labels: List[List[int]], 
                         validation_split: float = 0.2):
        """Train both HMM and ANN methods"""
        logger.info("Training double prediction method")
        
        # Split data
        split_idx = int(len(sequences) * (1 - validation_split))
        train_seqs, val_seqs = sequences[:split_idx], sequences[split_idx:]
        train_labels, val_labels = labels[:split_idx], labels[split_idx:]
        
        # Train HMM
        hmm_log_likelihood = self.hmm.train_baum_welch(train_seqs)
        
        # Prepare data for ANN (convert to tensors)
        train_data = self._prepare_ann_data(train_seqs, train_labels)
        val_data = self._prepare_ann_data(val_seqs, val_labels)
        
        # Train ANN
        self.ann.train_steepest_descent(train_data, val_data)
        
        return {
            'hmm_log_likelihood': hmm_log_likelihood,
            'validation_split': validation_split
        }
    
    def predict_structure(self, sequence: str) -> Dict[str, Any]:
        """Predict structure using both methods and combine results"""
        # HMM prediction
        hmm_path, hmm_prob = self.hmm.viterbi_decode(sequence)
        hmm_structure = [self.structure_labels[state] for state in hmm_path]
        
        # ANN prediction
        self.ann.eval()
        with torch.no_grad():
            sequence_tensor = self._sequence_to_tensor(sequence)
            ann_output = self.ann(sequence_tensor.unsqueeze(0))
            ann_prob, ann_pred = torch.max(ann_output, dim=1)
            ann_structure = [self.structure_labels[pred.item()] for pred in ann_pred]
        
        # Combine predictions (weighted ensemble)
        combined_structure = []
        confidence_scores = []
        
        for i, (hmm_state, ann_state) in enumerate(zip(hmm_structure, ann_structure)):
            # Weight by confidence (simple heuristic)
            hmm_weight = 0.4
            ann_weight = 0.6
            
            if hmm_state == ann_state:
                # Both methods agree - high confidence
                combined_structure.append(hmm_state)
                confidence_scores.append(0.9)
            else:
                # Methods disagree - use ANN (typically more accurate)
                combined_structure.append(ann_state)
                confidence_scores.append(0.7)
        
        return {
            'sequence': sequence,
            'hmm_prediction': hmm_structure,
            'ann_prediction': ann_structure,
            'combined_prediction': combined_structure,
            'confidence_scores': confidence_scores,
            'average_confidence': np.mean(confidence_scores),
            'hmm_probability': hmm_prob,
            'ann_confidence': ann_prob.item()
        }
    
    def _prepare_ann_data(self, sequences: List[str], labels: List[List[int]]):
        """Prepare data for ANN training"""
        # Convert sequences to tensors
        sequence_tensors = [self._sequence_to_tensor(seq) for seq in sequences]
        label_tensors = [torch.tensor(label, dtype=torch.long) for label in labels]
        
        return list(zip(sequence_tensors, label_tensors))
    
    def _sequence_to_tensor(self, sequence: str) -> torch.Tensor:
        """Convert sequence to tensor indices"""
        aa_mapping = self.hmm.aa_to_idx
        indices = [aa_mapping.get(aa.upper(), 0) for aa in sequence]
        return torch.tensor(indices, dtype=torch.long)

# Test function
def test_protein_prediction():
    """Test the double prediction method"""
    print("🧬 PROTEIN STRUCTURE PREDICTION TEST")
    print("=" * 50)
    
    # Sample protein sequences
    test_sequences = [
        "ACDEFGHIKLMNPQRSTVWY",  # All 20 amino acids
        "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAVDHERGLVDRFYKVELAPTHKGGFGLRGDGFNICKDG",  # Real protein fragment
        "GAVVAGNKVLTRGAFKTGLGAAVAGAKSTLNNNIAVAVAGN"  # Another protein fragment
    ]
    
    # Initialize double predictor
    predictor = DoublePredictor(hmm_states=5, ann_hidden=128)
    
    print("Testing predictions on sample sequences...")
    
    for i, sequence in enumerate(test_sequences, 1):
        print(f"\n🧪 Test {i}: Sequence length {len(sequence)}")
        print("-" * 30)
        
        result = predictor.predict_structure(sequence)
        
        print(f"Average confidence: {result['average_confidence']:.3f}")
        print(f"HMM probability: {result['hmm_probability']:.6f}")
        print(f"ANN confidence: {result['ann_confidence']:.3f}")
        
        # Show first 20 predictions
        combined_pred = result['combined_prediction'][:20]
        print(f"Combined prediction: {combined_pred}")
        
        # Count structure types
        structure_counts = {}
        for struct in combined_pred:
            structure_counts[struct] = structure_counts.get(struct, 0) + 1
        
        print(f"Structure distribution: {structure_counts}")

if __name__ == "__main__":
    test_protein_prediction()
