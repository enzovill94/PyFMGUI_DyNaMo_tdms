#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Concurrent Tether Analysis Module

This module provides concurrent processing capabilities for tether analysis,
allowing for multi-core batch processing of TDMS files using the same
pattern as the loadfiles.py concurrent implementation.

Features:
- Multi-core processing using ProcessPoolExecutor
- Progress tracking and error handling
- Memory efficient processing
- Compatible with existing tether_script analysis functions

Usage:
    from concurrent_tether_analysis import ConcurrentTetherProcessor
    
    processor = ConcurrentTetherProcessor()
    results = processor.process_files_concurrent(file_param_pairs, progress_callback)
"""

import os
import concurrent.futures
import numpy as np
import traceback
import multiprocessing as mp

def process_single_file_concurrent(filepath, params, use_nn=False, nn_threshold=0.5, auto_label=False):
    """
    Wrapper function for concurrent processing of single tether analysis.
    
    This function is designed to be run in a separate process, so it must
    import all necessary modules locally and handle all exceptions.
    
    Args:
        filepath (str): Path to the TDMS file to analyze
        params (dict): Analysis parameters dictionary
        use_nn (bool): Whether to run neural network analysis
        nn_threshold (float): Confidence threshold for NN plateau detection
        auto_label (bool): Whether to auto-label files based on NN results
        
    Returns:
        tuple: (filepath, result, error_message)
            - filepath: Original file path
            - result: Analysis result dictionary or None if failed
            - error_message: Error string if failed, None if successful
    """
    try:
        # Import tether analysis functions locally (required for multiprocessing)
        from tether_script import process_single_file
        
        # Validate inputs
        if not filepath or not os.path.exists(filepath):
            return (filepath, None, f"File not found: {filepath}")
        
        if not params:
            return (filepath, None, "No analysis parameters provided")
        
        # Run the traditional analysis
        result = process_single_file(filepath, params, save_plots=False)
        
        if result:
            # Add neural network analysis if enabled
            if use_nn:
                try:
                    # Import NN modules locally (required for multiprocessing)
                    import sys
                    from pathlib import Path
                    
                    # Add neural networks path
                    script_dir = Path(__file__).parent
                    nn_path = script_dir.parent / 'src'
                    if str(nn_path) not in sys.path:
                        sys.path.append(str(nn_path))
                    
                    from neural_networks.integration_example import TetherAnalysisWithNN
                    import numpy as np
                    
                    # Initialize NN analysis
                    nn_analysis = TetherAnalysisWithNN()
                    
                    # Get force and time data
                    force_data = result.get('defl_savitz', [])
                    time_data = result.get('rel_time', [])
                    
                    if len(force_data) > 0 and len(time_data) > 0:
                        # Run NN plateau detection
                        nn_results = nn_analysis.detect_plateaus_nn(
                            np.array(force_data), 
                            np.array(time_data),
                            confidence_threshold=nn_threshold
                        )
                        
                        # Add NN results to the main result
                        result['nn_plateau_results'] = nn_results
                        result['nn_plateaus'] = nn_results.get('plateaus', [])
                        nn_count = len(result['nn_plateaus'])
                        
                        # Auto-labeling logic
                        if auto_label:
                            if nn_count == 0:
                                result['auto_label'] = 'bad'
                                result['auto_label_reason'] = 'Neural network detected 0 plateaus'
                            else:
                                result['auto_label'] = 'good'
                                result['auto_label_reason'] = f'Neural network detected {nn_count} plateaus'
                        
                        print(f"NN analysis for {os.path.basename(filepath)}: {nn_count} plateaus detected")
                    else:
                        result['nn_plateau_results'] = None
                        result['nn_plateaus'] = []
                        if auto_label:
                            result['auto_label'] = 'bad'
                            result['auto_label_reason'] = 'Empty force/time data'
                            
                except Exception as nn_error:
                    print(f"Neural network analysis failed for {os.path.basename(filepath)}: {nn_error}")
                    result['nn_plateau_results'] = None
                    result['nn_plateaus'] = []
                    if auto_label:
                        result['auto_label'] = 'bad'
                        result['auto_label_reason'] = f'NN analysis failed: {str(nn_error)}'
            else:
                # No NN analysis requested
                result['nn_plateau_results'] = None
                result['nn_plateaus'] = []
            # Success - return the result
            return (filepath, result, None)
        else:
            # Analysis returned no results
            return (filepath, None, "Analysis returned no results")
            
    except ImportError as e:
        return (filepath, None, f"Import error: {str(e)}. Make sure tether_script.py is in the Python path.")
    except Exception as e:
        # Capture full error traceback for debugging
        error_msg = f"Analysis failed: {str(e)}\n{traceback.format_exc()}"
        return (filepath, None, error_msg)

class ConcurrentTetherProcessor:
    """
    Concurrent processor for tether analysis using multiple CPU cores.
    
    This class manages the parallel execution of tether analysis across
    multiple files, providing progress tracking and error handling.
    """
    
    def __init__(self, max_workers=None):
        """
        Initialize the concurrent processor.
        
        Args:
            max_workers (int, optional): Maximum number of worker processes.
                                       If None, uses CPU count.
        """
        self.max_workers = max_workers or mp.cpu_count()
        self.results_cache = {}
        
    def validate_inputs(self, file_param_pairs):
        """
        Validate input file-parameter pairs.
        
        Args:
            file_param_pairs (list): List of (filepath, params) tuples
            
        Returns:
            tuple: (valid_pairs, invalid_pairs) where each is a list
        """
        valid_pairs = []
        invalid_pairs = []
        
        for pair in file_param_pairs:
            if len(pair) != 2:
                invalid_pairs.append((pair, "Invalid pair format - expected (filepath, params)"))
                continue
                
            filepath, params = pair
            
            if not filepath or not isinstance(filepath, str):
                invalid_pairs.append((pair, "Invalid filepath"))
                continue
                
            if not os.path.exists(filepath):
                invalid_pairs.append((pair, f"File not found: {filepath}"))
                continue
                
            if not filepath.endswith('.tdms'):
                invalid_pairs.append((pair, "Not a TDMS file"))
                continue
                
            if not params or not isinstance(params, dict):
                invalid_pairs.append((pair, "Invalid parameters"))
                continue
                
            valid_pairs.append(pair)
        
        return valid_pairs, invalid_pairs
    
    def process_files_concurrent(self, file_param_pairs, progress_callback=None, error_callback=None,
                               use_nn=False, nn_threshold=0.5, auto_label=False):
        """
        Process multiple files concurrently using multiple CPU cores.
        
        Args:
            file_param_pairs (list): List of (filepath, params) tuples
            progress_callback (callable, optional): Function called with (completed_count, total_count)
            error_callback (callable, optional): Function called with (filepath, error_message)
            use_nn (bool): Whether to run neural network analysis
            nn_threshold (float): Confidence threshold for NN plateau detection
            auto_label (bool): Whether to auto-label files based on NN results
            
        Returns:
            dict: Dictionary mapping filepath -> analysis_result for successful analyses
        """
        if not file_param_pairs:
            return {}
        
        # Validate inputs
        valid_pairs, invalid_pairs = self.validate_inputs(file_param_pairs)
        
        # Report invalid files
        for pair, error_msg in invalid_pairs:
            if error_callback:
                filepath = pair[0] if len(pair) > 0 else "Unknown"
                error_callback(filepath, error_msg)
        
        if not valid_pairs:
            return {}
        
        total_files = len(valid_pairs)
        results = {}
        completed_count = 0
        
        nn_status = f" with NN analysis (threshold={nn_threshold})" if use_nn else ""
        auto_label_status = " and auto-labeling" if auto_label else ""
        print(f"Starting concurrent analysis of {total_files} files using {self.max_workers} workers{nn_status}{auto_label_status}...")
        
        try:
            with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks with NN parameters
                future_to_filepath = {
                    executor.submit(process_single_file_concurrent, filepath, params, use_nn, nn_threshold, auto_label): filepath
                    for filepath, params in valid_pairs
                }
                
                # Process completed tasks as they finish
                for future in concurrent.futures.as_completed(future_to_filepath):
                    filepath = future_to_filepath[future]
                    completed_count += 1
                    
                    try:
                        # Get the result
                        result_filepath, analysis_result, error_message = future.result()
                        
                        if error_message:
                            # Analysis failed
                            if error_callback:
                                error_callback(filepath, error_message)
                            print(f"✗ Failed to analyze {os.path.basename(filepath)}: {error_message}")
                        else:
                            # Analysis succeeded
                            results[filepath] = analysis_result
                            plateau_count = len(analysis_result['plateaus']) if analysis_result.get('plateaus') else 0
                            nn_count = len(analysis_result.get('nn_plateaus', []))
                            auto_label_info = f" -> {analysis_result.get('auto_label', 'no label')}" if auto_label else ""
                            
                            if use_nn:
                                print(f"✓ Analyzed {os.path.basename(filepath)}: {plateau_count} traditional, {nn_count} NN plateaus{auto_label_info}")
                            else:
                                print(f"✓ Analyzed {os.path.basename(filepath)}: {plateau_count} plateaus found")
                        
                        # Update progress
                        if progress_callback:
                            progress_callback(completed_count, total_files)
                            
                    except Exception as e:
                        # Handle future execution errors
                        if error_callback:
                            error_callback(filepath, f"Future execution error: {str(e)}")
                        print(f"✗ Future execution error for {os.path.basename(filepath)}: {str(e)}")
        
        except Exception as e:
            print(f"Concurrent processing error: {str(e)}")
            if error_callback:
                error_callback("ProcessPool", f"Concurrent processing failed: {str(e)}")
        
        print(f"Concurrent analysis complete: {len(results)}/{total_files} files processed successfully")
        return results
    
    def get_analysis_summary(self, results):
        """
        Generate a summary of analysis results.
        
        Args:
            results (dict): Results from process_files_concurrent
            
        Returns:
            dict: Summary statistics
        """
        if not results:
            return {
                'total_analyzed': 0,
                'total_plateaus': 0,
                'avg_plateaus_per_file': 0,
                'files_with_plateaus': 0,
                'velocity_stats': {}
            }
        
        total_analyzed = len(results)
        total_plateaus = 0
        files_with_plateaus = 0
        velocities = []
        
        for filepath, result in results.items():
            plateaus = result.get('plateaus', [])
            plateau_count = len(plateaus) if plateaus else 0
            total_plateaus += plateau_count
            
            if plateau_count > 0:
                files_with_plateaus += 1
            
            # Collect velocity data
            if 'velocity_calc_um_s' in result:
                vel = result['velocity_calc_um_s']
                if isinstance(vel, (int, float)) and not np.isnan(vel):
                    velocities.append(vel)
        
        # Calculate velocity statistics
        velocity_stats = {}
        if velocities:
            velocity_stats = {
                'count': len(velocities),
                'mean': np.mean(velocities),
                'std': np.std(velocities),
                'min': np.min(velocities),
                'max': np.max(velocities),
                'median': np.median(velocities)
            }
        
        return {
            'total_analyzed': total_analyzed,
            'total_plateaus': total_plateaus,
            'avg_plateaus_per_file': total_plateaus / total_analyzed if total_analyzed > 0 else 0,
            'files_with_plateaus': files_with_plateaus,
            'velocity_stats': velocity_stats
        }

# Convenience function for simple usage
def analyze_files_concurrent(file_paths, parameters, max_workers=None, progress_callback=None):
    """
    Convenience function to analyze multiple files with the same parameters.
    
    Args:
        file_paths (list): List of file paths to analyze
        parameters (dict): Analysis parameters to use for all files
        max_workers (int, optional): Maximum number of worker processes
        progress_callback (callable, optional): Progress callback function
        
    Returns:
        dict: Results dictionary mapping filepath -> analysis_result
    """
    # Create file-parameter pairs
    file_param_pairs = [(filepath, parameters.copy()) for filepath in file_paths]
    
    # Create processor and run analysis
    processor = ConcurrentTetherProcessor(max_workers=max_workers)
    results = processor.process_files_concurrent(file_param_pairs, progress_callback=progress_callback)
    
    return results

if __name__ == "__main__":
    # Example usage and testing
    print("Concurrent Tether Analysis Module")
    print(f"Available CPU cores: {mp.cpu_count()}")
    print("Import this module to use concurrent processing in your GUI.")
