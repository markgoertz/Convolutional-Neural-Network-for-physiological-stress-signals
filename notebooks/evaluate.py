from pathlib import Path
import numpy as np
import pandas as pd
import pickle
import matplotlib.pyplot as plt
import seaborn as sns
from tensorflow.keras.models import load_model
from dvclive import Live
from helper import F1Score
import plotly.graph_objects as go

def create_segments(time_indices, values, stress_periods):
    segments = []
    current_segment = {"x": [], "y": [], "color": "blue"}
    for t, v in zip(time_indices, values):
        in_stress = any(start <= t < end for start, end in stress_periods)
        color = "red" if in_stress else "blue"

        if color != current_segment["color"] and current_segment["x"]:
            segments.append(current_segment)
            current_segment = {"x": [], "y": [], "color": color}

        current_segment["x"].append(t)
        current_segment["y"].append(v)
        current_segment["color"] = color

    if current_segment["x"]:
        segments.append(current_segment)
    
    return segments

def plot_physiological_signals(x_test_path, y_test_path, model, subject_id):
    
    with Live() as live:
        # Load x_test and y_test from pickle files
        with open(x_test_path, "rb") as f:
            x_test = pickle.load(f)
        with open(y_test_path, "rb") as f:
            y_test = pickle.load(f)

        # Ensure x_test contains required keys
        required_keys = ['EDA', 'TEMP', 'BVP', 'ACC']
        for key in required_keys:
            if key not in x_test:
                raise ValueError(f"Missing required key '{key}' in x_test pickle file.")

        # Extract signals
        eda, temp, bvp, acc = x_test['EDA'], x_test['TEMP'], x_test['BVP'], x_test['ACC']

        # Reshape and preprocess signals for the model
        data_dict = {
            'EDA': np.array(eda).reshape(-1, 32, 1),
            'TEMP': np.array(temp).reshape(-1, 32, 1),
            'BVP': np.array(bvp).reshape(-1, 256, 1),
            'ACC': np.array(acc).reshape(-1, 256, 1)
        }

        # Make predictions
        y_pred_probs = model.predict([data_dict['EDA'], data_dict['BVP'], data_dict['TEMP'], data_dict['ACC']])
        y_pred = (y_pred_probs > 0.5).astype(int).flatten()
        
        live.log_plot("confusion_matrix", y_test, y_pred, name=f"confusion_matrix subject: {subject_id}") 
        
        # Create time indices for signals
        eda_time_indices = np.arange(len(eda)).tolist()

        # Define stress periods based on true and predicted labels
        stress_periods = [(i * 8, (i + 1) * 8) for i, label in enumerate(y_test) if label == 1]
        predicted_stress_periods = [(i * 8, (i + 1) * 8) for i, pred in enumerate(y_pred) if pred == 1]

        # Initialize the Plotly figure
        fig = go.Figure()

        # Add EDA signal
        fig.add_trace(go.Scatter(
            x=eda_time_indices,
            y=eda,
            mode='lines',
            name='EDA',
            line=dict(color='blue'),
            showlegend=True
        ))

        # Add green background for true stress periods
        for start, end in stress_periods:
            fig.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                fillcolor="rgba(0,255,0,0.2)",
                line=dict(width=0)
            )

        # Add red background for predicted stress periods
        for start, end in predicted_stress_periods:
            fig.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                fillcolor="rgba(255,0,0,0.3)",
                line=dict(width=0)
            )

        # Update layout for the figure
        fig.update_layout(
            title=f'Physiological Signals with Stress Periods of subject {subject_id}',
            xaxis_title='Time (seconds)',
            yaxis_title='Signal Value',
            legend_title='Signals',
            template='plotly_white'
        )

        # Save and log the plot image
        plot_path = "images/evaluation/plots/physiological_signals_plot.png"
        fig.write_image(plot_path)
        live.log_image("physiological_signals", plot_path)

        return fig

# Evaluation function
def evaluate():
   
    # Load model and helper data
    model_path = Path("models") / "best_model.h5"
    model = load_model(model_path, custom_objects={'F1Score': F1Score})
    print(model.summary())
    
    plot_physiological_signals(
        "data/results/x_test_1.pkl",
        "data/results/y_test_1.pkl",
        model,
        "S16"
    )
    print("Evaluation complete.")

if __name__ == "__main__":
    evaluate()
