import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import numpy as np
from sklearn.model_selection import train_test_split
from model import EEGNet

def load_data(data_dir, condition_filter=None):
    """
    Loads the numpy arrays exported by preprocessing.py.
    condition_filter: 0 (Pronounced), 1 (Inner), 2 (Visualized), or None (All)
    """
    x_path = os.path.join(data_dir, "X.npy")
    y_words_path = os.path.join(data_dir, "y_words.npy")
    y_conds_path = os.path.join(data_dir, "y_conditions.npy")
    sub_ids_path = os.path.join(data_dir, "subject_ids.npy")
    
    print("Loading data...")
    X = np.load(x_path)
    y_words = np.load(y_words_path)
    y_conds = np.load(y_conds_path)
    sub_ids = np.load(sub_ids_path)
    
    if condition_filter is not None:
        mask = (y_conds == condition_filter)
        X = X[mask]
        y_words = y_words[mask]
        sub_ids = sub_ids[mask]
        print(f"Filtered for Condition {condition_filter}")
        
    print(f"Loaded X shape: {X.shape}, y shape: {y_words.shape}")
    
    # Z-score normalization per channel per trial
    mean = np.mean(X, axis=2, keepdims=True)
    std = np.std(X, axis=2, keepdims=True)
    X = (X - mean) / (std + 1e-8)
    
    # ACTION INTERVAL CROP: t = +1.0s to +3.5s 
    # Start Index = (-0.5s to 1.0s) = 1.5s * 256Hz = 384
    # End Index = (-0.5s to 3.5s) = 4.0s * 256Hz = 1024
    print("Cropping signals STRICTLY to the 'Action Interval' [1.0s to 3.5s] to eliminate visual cue leakage...")
    start_idx = 384
    end_idx = 1024 
    X = X[:, :, start_idx:end_idx]
    print(f"Cropped X shape: {X.shape}")
    
    return X, y_words, sub_ids

def get_dataloaders(X, y, sub_ids, batch_size=32, test_subjects=[9, 10]):
    """
    Splits the data into Training and Testing sets specifically keeping the sets 
    Subject-Independent. E.g. Train on sub 1-8, Test on sub 9-10.
    """
    test_mask = np.isin(sub_ids, test_subjects)
    train_mask = ~test_mask
    
    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    
    print(f"Subject-Independent Split: Train Subjects = {np.unique(sub_ids[train_mask])}, Test Subjects = {test_subjects}")
    print(f"Training set: {X_train.shape[0]} samples")
    print(f"Testing set: {X_test.shape[0]} samples")
    
    # Convert numpy arrays to PyTorch Tensors.
    train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.float32), 
                                  torch.tensor(y_train, dtype=torch.long))
    test_dataset = TensorDataset(torch.tensor(X_test, dtype=torch.float32), 
                                 torch.tensor(y_test, dtype=torch.long))
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
    
    return train_loader, test_loader

def train_model(model, train_loader, test_loader, num_epochs=30, learning_rate=1e-3):
    # Determine the fastest processing core automatically (Mac: MPS, PC: CUDA, else: CPU)
    if torch.backends.mps.is_available():
        device = torch.device('mps')
    elif torch.cuda.is_available():
        device = torch.device('cuda')
    else:
        device = torch.device('cpu')
        
    print(f"Using device: {device}")
    model = model.to(device)
    
    # We use CrossEntropyLoss for independent multi-class classification
    criterion = nn.CrossEntropyLoss()
    
    # Adam optimizer works great for convolutional layers and has weight decay to reduce overfitting
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-2)
    
    # Cosine Annealing slowly drops the learning rate over the epochs
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs, eta_min=1e-6)
    
    best_acc = 0.0
    
    for epoch in range(num_epochs):
        # -----------------------------
        # Training Phase
        # -----------------------------
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for inputs, targets in train_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item() * inputs.size(0)
            
            # Highest logit wins
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
            
        train_loss = running_loss / total
        train_acc = 100. * correct / total
        
        # -----------------------------
        # Evaluation Phase
        # -----------------------------
        model.eval()
        test_loss = 0.0
        correct = 0
        total = 0
        
        # Don't construct computation graphs for test evaluation to save time + memory
        with torch.no_grad():
            for inputs, targets in test_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                test_loss += loss.item() * inputs.size(0)
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
                
        test_loss = test_loss / total
        test_acc = 100. * correct / total
        
        scheduler.step()
        
        # If model got visibly better on test data unseen before, save this current weight dictionary!
        if test_acc > best_acc:
            best_acc = test_acc
            torch.save(model.state_dict(), 'best_model.pth')
            best_marker = "(*New Best*)"
        else:
            best_marker = ""
            
        print(f"Epoch [{epoch+1:2d}/{num_epochs:2d}] "
              f"Train Loss: {train_loss:.4f} Acc: {train_acc:.2f}% | "
              f"Test Loss: {test_loss:.4f} Acc: {test_acc:.2f}% {best_marker}")
              
    print(f"\nTraining finished! Best Validation Accuracy achieved: {best_acc:.2f}%")
    print("Best model weights successfully saved to 'best_model.pth'")

def main():
    data_dir = "processed_data"
    
    if not os.path.exists(os.path.join(data_dir, "X.npy")):
        print(f"Error: Processed data not found in {data_dir}/. Please run preprocessing.py first.")
        return
        
    # By default, train on ALL conditions (condition_filter=None)
    # You can change condition_filter to 0 (Pronounced), 1 (Inner), or 2 (Visualized)
    X, y, sub_ids = load_data(data_dir, condition_filter=None)
    
    # Do a Subject-Independent Split (Train on Subject 1-8, Test on Subject 9-10)
    train_loader, test_loader = get_dataloaders(X, y, sub_ids, batch_size=32, test_subjects=[9, 10])
    
    # Initialize the model natively setup for 128 Channels.
    model = EEGNet(num_classes=4, in_channels=128)
    
    # Start the training!
    train_model(model, train_loader, test_loader, num_epochs=400, learning_rate=0.001)

if __name__ == "__main__":
    main()
