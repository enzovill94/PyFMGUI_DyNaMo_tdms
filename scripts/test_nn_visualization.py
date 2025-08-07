#!/usr/bin/env python3
"""
Neural Network Plateau Detection Visualization Test

This script creates test data and visualizes how the neural network
detects plateaus compared to traditional methods.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add the PyFMGUI_DyNaMo/src directory to the path so we can import neural networks
current_dir = Path(__file__).parent
gui_src_dir = current_dir.parent / "src"
sys.path.insert(0, str(gui_src_dir))

try:
    from neural_networks.integration_example import TetherAnalysisWithNN
    print("Successfully imported neural network modules")
except ImportError as e:
    print(f"Error importing neural network modules: {e}")
    print("Make sure you're in the right directory and the neural networks are installed")
    print(f"Looking for modules in: {gui_src_dir}")
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
        
        # Plateau region (constant force)
        plateau_mask = (time >= 3) & (time <= 7)
        force[plateau_mask] = 2.0 + 0.1 * np.sin(2 * np.pi * time[plateau_mask] / 2)  # Small oscillation
        
        # Rupture (sudden drop then increase)
        rupture_mask = time > 7
        rupture_time = time[rupture_mask] - 7
        force[rupture_mask] = 0.5 + 0.3 * rupture_time**1.5
        
    else:
        # Create a force curve without a clear plateau
        force = 0.1 * time**2 + 0.05 * np.sin(5 * time) + 0.1 * np.random.randn(n_points) * noise_level
    
    # Add noise
    force += np.random.randn(n_points) * noise_level
    
    return time, force


def visualize_nn_detection():
    """
    Create visualizations showing NN plateau detection
    """
    print("Creating neural network analysis instance...")
    try:
        nn_analysis = TetherAnalysisWithNN()
        print("Neural network analysis created successfully")
    except Exception as e:
        print(f"Error creating neural network analysis: {e}")
        return
    
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
            nn_results = nn_analysis.detect_plateaus_nn(
                force_data, 
                time_data, 
                confidence_threshold=0.1
            )
            
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
            ax.set_title(f'{title}\nNN Analysis Failed')
        
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


def test_confidence_threshold_effect():
    """
    Test how different confidence thresholds affect detection
    """
    print("\nTesting confidence threshold effects...")
    
    try:
        nn_analysis = TetherAnalysisWithNN()
        
        # Generate test data with a moderate plateau
        time_data, force_data = create_synthetic_tether_data(
            n_points=1000, 
            with_plateau=True, 
            noise_level=0.1
        )
        
        # Test different thresholds
        thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
        
        fig, axes = plt.subplots(1, len(thresholds), figsize=(20, 4))
        fig.suptitle('Effect of Confidence Threshold on NN Plateau Detection', fontsize=14)
        
        for i, threshold in enumerate(thresholds):
            ax = axes[i]
            
            # Plot data
            ax.plot(time_data, force_data, 'b-', alpha=0.7, linewidth=1, label='Force Data')
            
            # Run NN analysis with this threshold
            nn_results = nn_analysis.detect_plateaus_nn(
                force_data, 
                time_data, 
                confidence_threshold=threshold
            )
            
            # Visualize results
            for j, plateau in enumerate(nn_results['plateaus']):
                start_time = plateau['start_time']
                end_time = plateau['end_time']
                
                plateau_mask = (time_data >= start_time) & (time_data <= end_time)
                if np.any(plateau_mask):
                    ax.fill_between(
                        time_data[plateau_mask], 
                        force_data[plateau_mask], 
                        alpha=0.4, 
                        color='red'
                    )
                
                ax.axvline(start_time, color='red', linestyle='--', alpha=0.8)
                ax.axvline(end_time, color='red', linestyle='--', alpha=0.8)
            
            ax.set_title(f'Threshold: {threshold}\nPlateaus: {len(nn_results["plateaus"])}')
            ax.set_xlabel('Time (s)')
            if i == 0:
                ax.set_ylabel('Force (nN)')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save threshold comparison
        threshold_path = current_dir / "nn_threshold_comparison.png"
        plt.savefig(threshold_path, dpi=300, bbox_inches='tight')
        print(f"Threshold comparison saved to: {threshold_path}")
        
        plt.show()
        
    except Exception as e:
        print(f"Error in threshold testing: {e}")


def main():
    """
    Main function to run all visualization tests
    """
    print("=" * 60)
    print("Neural Network Plateau Detection Visualization Test")
    print("=" * 60)
    
    try:
        # Test basic visualization
        visualize_nn_detection()
        
        # Test threshold effects
        test_confidence_threshold_effect()
        
        print("\n" + "=" * 60)
        print("Visualization test completed successfully!")
        print("Check the generated PNG files for the results.")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error during visualization test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
