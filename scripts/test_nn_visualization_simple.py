#!/usr/bin/env python3
"""
Simple Neural Network Plateau Detection Visualization

This script creates test data and visualizes how the neural network
detects plateaus. It directly uses the neural network models.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add the PyFMGUI_DyNaMo/src directory to the path
current_dir = Path(__file__).parent
gui_src_dir = current_dir.parent / "src"
sys.path.insert(0, str(gui_src_dir))

try:
    from neural_networks.plateau_detector import create_plateau_detector_model, PlateauDetectorNN
    from neural_networks.utils.data_preprocessing import TetherDataPreprocessor
    import torch
    print("Successfully imported neural network modules")
except ImportError as e:
    print(f"Error importing neural network modules: {e}")
    print("Make sure you're in the PyFMGUI_DyNaMo directory and neural networks are set up")
    print(f"Looking for modules in: {gui_src_dir}")
    print("\nTrying alternative approach...")
    
    try:
        # Try to import from current working directory
        sys.path.insert(0, str(current_dir.parent / "src"))
        from neural_networks.plateau_detector import create_plateau_detector_model
        print("Successfully imported from alternative path")
    except ImportError:
        print("Could not import neural network modules. Please check your setup.")
        sys.exit(1)


def create_synthetic_tether_data(n_points=1000, with_plateau=True, noise_level=0.1):
    """
    Create synthetic tether data for testing visualization
    """
    time = np.linspace(0, 10, n_points)
    
    if with_plateau:
        # Create a force curve with a plateau
        force = np.zeros_like(time)
        
        # Initial approach (increasing force)
        approach_mask = time < 3
        force[approach_mask] = 0.2 * time[approach_mask]**2
        
        # Plateau region (constant force with small oscillations)
        plateau_mask = (time >= 3) & (time <= 7)
        force[plateau_mask] = 2.0 + 0.1 * np.sin(2 * np.pi * time[plateau_mask] / 2)
        
        # Rupture (sudden drop then increase)
        rupture_mask = time > 7
        rupture_time = time[rupture_mask] - 7
        force[rupture_mask] = 0.5 + 0.3 * rupture_time**1.5
        
    else:
        # Create a force curve without a clear plateau
        force = 0.1 * time**2 + 0.05 * np.sin(5 * time)
    
    # Add noise
    force += np.random.randn(n_points) * noise_level
    
    return time, force


def simple_nn_analysis(force_data, time_data, confidence_threshold=0.5):
    """
    Simple neural network analysis function
    """
    try:
        # Create model
        model = create_plateau_detector_model()
        
        # Create preprocessor
        preprocessor = TetherDataPreprocessor()
        
        # Preprocess data
        input_tensor = preprocessor.prepare_inference_data(force_data, time_data)
        
        # Run inference
        model.eval()
        with torch.no_grad():
            outputs = model(input_tensor)
        
        # Extract results
        classification_prob = torch.sigmoid(outputs['classification']).item()
        has_plateau = classification_prob > confidence_threshold
        
        # Extract boundary predictions (these are normalized 0-1)
        boundaries = outputs['boundaries'].squeeze().numpy()
        
        results = {
            'has_plateau': has_plateau,
            'confidence': classification_prob,
            'plateaus': []
        }
        
        if has_plateau:
            # Convert normalized boundaries back to actual values
            start_time_norm, end_time_norm, start_force_norm, end_force_norm = boundaries
            
            # Denormalize
            time_min, time_max = time_data.min(), time_data.max()
            force_min, force_max = force_data.min(), force_data.max()
            
            start_time = start_time_norm * (time_max - time_min) + time_min
            end_time = end_time_norm * (time_max - time_min) + time_min
            start_force = start_force_norm * (force_max - force_min) + force_min
            end_force = end_force_norm * (force_max - force_min) + force_min
            
            plateau = {
                'start_time': start_time,
                'end_time': end_time,
                'start_force': start_force,
                'end_force': end_force,
                'confidence': classification_prob
            }
            results['plateaus'].append(plateau)
        
        return results
        
    except Exception as e:
        print(f"Error in NN analysis: {e}")
        return {
            'has_plateau': False,
            'confidence': 0.0,
            'plateaus': [],
            'error': str(e)
        }


def visualize_nn_detection():
    """
    Create visualizations showing NN plateau detection
    """
    print("Creating neural network visualization...")
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Neural Network Plateau Detection Visualization', fontsize=16)
    
    # Test cases
    test_cases = [
        ("Clear Plateau", True, 0.05),
        ("Noisy Plateau", True, 0.15),
        ("No Plateau", False, 0.1),
        ("Weak Signal", True, 0.25)
    ]
    
    for idx, (title, has_plateau, noise_level) in enumerate(test_cases):
        ax = axes[idx // 2, idx % 2]
        
        print(f"Generating test case: {title}")
        
        # Generate synthetic data
        time_data, force_data = create_synthetic_tether_data(
            n_points=1000, 
            with_plateau=has_plateau, 
            noise_level=noise_level
        )
        
        # Plot original data
        ax.plot(time_data, force_data, 'b-', alpha=0.7, linewidth=1, label='Force Data')
        
        try:
            # Run neural network analysis
            print(f"Running NN analysis for {title}...")
            nn_results = simple_nn_analysis(
                force_data, 
                time_data, 
                confidence_threshold=0.1
            )
            
            if 'error' in nn_results:
                print(f"NN Error for {title}: {nn_results['error']}")
                ax.set_title(f'{title}\nNN Analysis Failed')
            else:
                print(f"NN Results for {title}:")
                print(f"  - Has plateau: {nn_results['has_plateau']}")
                print(f"  - Confidence: {nn_results['confidence']:.3f}")
                print(f"  - Number of plateaus: {len(nn_results['plateaus'])}")
                
                # Visualize detected plateaus
                for i, plateau in enumerate(nn_results['plateaus']):
                    start_time = plateau['start_time']
                    end_time = plateau['end_time']
                    confidence = plateau['confidence']
                    
                    print(f"  - Plateau {i+1}: {start_time:.2f}s - {end_time:.2f}s, confidence: {confidence:.3f}")
                    
                    # Highlight plateau region
                    plateau_mask = (time_data >= start_time) & (time_data <= end_time)
                    if np.any(plateau_mask):
                        ax.fill_between(
                            time_data[plateau_mask], 
                            force_data[plateau_mask], 
                            alpha=0.3, 
                            color='red',
                            label=f'NN Plateau {i+1} (conf: {confidence:.2f})'
                        )
                    
                    # Mark boundaries
                    ax.axvline(start_time, color='red', linestyle='--', alpha=0.8)
                    ax.axvline(end_time, color='red', linestyle='--', alpha=0.8)
                    
                    # Add text annotation
                    mid_time = (start_time + end_time) / 2
                    ax.annotate(
                        f'NN: {confidence:.2f}',
                        xy=(mid_time, np.max(force_data) * 0.9),
                        ha='center',
                        fontsize=10,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="red", alpha=0.3)
                    )
                
                # Add overall confidence to title
                ax.set_title(f'{title}\nNN Confidence: {nn_results["confidence"]:.3f}')
            
        except Exception as e:
            print(f"Error during NN analysis for {title}: {e}")
            ax.set_title(f'{title}\nNN Analysis Error')
            ax.text(0.5, 0.5, f'Error: {str(e)[:50]}...', 
                   transform=ax.transAxes, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.5))
        
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Force (nN)')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
    
    plt.tight_layout()
    
    # Save the plot
    output_path = current_dir / "nn_plateau_visualization.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to: {output_path}")
    
    # Show the plot
    plt.show()


def test_with_mock_data():
    """
    Test with simple mock data to show how the visualization would look
    """
    print("Creating mock data visualization...")
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Mock Neural Network Plateau Detection Examples', fontsize=16)
    
    # Test case 1: Clear plateau
    time1, force1 = create_synthetic_tether_data(with_plateau=True, noise_level=0.05)
    axes[0].plot(time1, force1, 'b-', alpha=0.7, linewidth=1, label='Force Data')
    
    # Mock detected plateau (manually set for demonstration)
    plateau_start, plateau_end = 3.0, 7.0
    plateau_mask = (time1 >= plateau_start) & (time1 <= plateau_end)
    axes[0].fill_between(time1[plateau_mask], force1[plateau_mask], 
                        alpha=0.3, color='red', label='NN Detected Plateau (conf: 0.85)')
    axes[0].axvline(plateau_start, color='red', linestyle='--', alpha=0.8)
    axes[0].axvline(plateau_end, color='red', linestyle='--', alpha=0.8)
    axes[0].set_title('High Confidence Detection\nNN Confidence: 0.85')
    axes[0].set_xlabel('Time (s)')
    axes[0].set_ylabel('Force (nN)')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    # Test case 2: Noisy plateau
    time2, force2 = create_synthetic_tether_data(with_plateau=True, noise_level=0.2)
    axes[1].plot(time2, force2, 'b-', alpha=0.7, linewidth=1, label='Force Data')
    
    # Mock detected plateau with lower confidence
    plateau_mask2 = (time2 >= 2.8) & (time2 <= 7.2)
    axes[1].fill_between(time2[plateau_mask2], force2[plateau_mask2], 
                        alpha=0.3, color='orange', label='NN Detected Plateau (conf: 0.45)')
    axes[1].axvline(2.8, color='orange', linestyle='--', alpha=0.8)
    axes[1].axvline(7.2, color='orange', linestyle='--', alpha=0.8)
    axes[1].set_title('Medium Confidence Detection\nNN Confidence: 0.45')
    axes[1].set_xlabel('Time (s)')
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    
    # Test case 3: No plateau
    time3, force3 = create_synthetic_tether_data(with_plateau=False, noise_level=0.1)
    axes[2].plot(time3, force3, 'b-', alpha=0.7, linewidth=1, label='Force Data')
    axes[2].set_title('No Plateau Detected\nNN Confidence: 0.15')
    axes[2].set_xlabel('Time (s)')
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()
    
    plt.tight_layout()
    
    # Save mock visualization
    mock_path = current_dir / "nn_mock_visualization.png"
    plt.savefig(mock_path, dpi=300, bbox_inches='tight')
    print(f"Mock visualization saved to: {mock_path}")
    
    plt.show()


def main():
    """
    Main function to run visualization tests
    """
    print("=" * 60)
    print("Neural Network Plateau Detection Visualization Test")
    print("=" * 60)
    
    # First try with mock data (always works)
    print("\n1. Creating mock data visualization...")
    test_with_mock_data()
    
    # Then try with actual neural network
    print("\n2. Testing with actual neural network...")
    try:
        visualize_nn_detection()
        print("\nVisualization test completed successfully!")
    except Exception as e:
        print(f"Error with neural network visualization: {e}")
        print("Mock visualization was created successfully.")
    
    print("\n" + "=" * 60)
    print("Check the generated PNG files for the results:")
    print("- nn_mock_visualization.png (mock data, always available)")
    print("- nn_plateau_visualization.png (actual NN, if successful)")
    print("=" * 60)


if __name__ == "__main__":
    main()
