# Action-Aligned Riemannian Decoding for Inner Speech

This repository contains the implementation of a decoding pipeline designed to identify intended words from EEG signals during inner and pronounced speech. The project focuses on utilizing **Riemannian Geometry** and **FilterBank** approaches to achieve high-fidelity neural signal classification.

## 🚀 Key Features

- **FilterBank Riemannian (FBR)**: Captures spectral-spatial signatures across multiple neural frequencies (Theta, Alpha, Beta, and Gamma).
- **Action-Aligned Epoching**: Strictly causal filtering and specific temporal windowing ([0.5, 3.0]s) for real-time demo readiness.
- **Unicorn Headset Simulation**: Support for 8-channel Unicorn headset configurations to establish realistic performance baselines.

## 🛠️ Installation

Ensure you have Python installed. You can install the required dependencies using the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Dependencies
- `mne`: EEG data handling and processing.
- `pyriemann`: Riemannian geometry for BCI.
- `scikit-learn`: Machine learning tools and pipelines.
- `numpy` & `pandas`: Data manipulation.

## 📂 Project Structure

- `main.py`: The evaluation dashboard. Runs the Riemannian decoding pipeline and outputs performance metrics.
- `model.py`: Contains the `FilterBankRiemannian` transformer and model pipeline definition.
- `preprocessing.py`: Handles raw data loading, event correction, filtering, and epoching for the `ds003626` dataset.
- `requirements.txt`: Project dependency list.

## 📖 Usage

### 1. Data Preprocessing
Before running the evaluation, the raw data needs to be processed.
*Note: Ensure the `ds003626` dataset is available in your project root.*

```bash
python preprocessing.py
```

### 2. Running the Decoding Pipeline
Execute the main script to run the cross-validation evaluation and view the accuracy dashboard.

```bash
python main.py
```

## 🧠 Model Architecture

The core of the system is the `FilterBankRiemannian` model. It decomposes the EEG signal into four frequency bands:
- **Theta/Alpha** (4-12 Hz)
- **Beta** (12-30 Hz)
- **Low Gamma** (30-45 Hz)
- **High Gamma** (45-90 Hz)

For each band, it estimates the **Covariance Matrix** and maps it to a **Tangent Space** using Riemannian metrics before classification with a calibrated Logistic Regression model.

---
*Created for the Neuroscience Hackathon - Imperial College London.*