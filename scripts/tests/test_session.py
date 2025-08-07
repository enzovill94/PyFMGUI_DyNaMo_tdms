#!/usr/bin/env python3
"""
Test script to diagnose session loading issues
"""

import pandas as pd
import os
import json

def test_session_file(session_file_path):
    """Test loading a session CSV file to identify issues"""
    
    print(f"Testing session file: {session_file_path}")
    print("=" * 50)
    
    # Check if file exists
    if not os.path.exists(session_file_path):
        print("❌ ERROR: Session file does not exist!")
        return False
    
    try:
        # Try to load the CSV
        df_session = pd.read_csv(session_file_path)
        print(f"✅ CSV loaded successfully")
        print(f"   Rows: {len(df_session)}")
        print(f"   Columns: {list(df_session.columns)}")
        
        # Check for required columns
        required_columns = ['local_file_path', 'file_name', 'bool_good_curve']
        missing_columns = [col for col in required_columns if col not in df_session.columns]
        
        if missing_columns:
            print(f"❌ ERROR: Missing required columns: {missing_columns}")
            return False
        else:
            print(f"✅ All required columns present")
        
        # Check for session metadata
        if (len(df_session) > 0 and 
            df_session.iloc[0]['local_file_path'] == 'SESSION_METADATA'):
            print("✅ Session metadata found")
            try:
                metadata_row = df_session.iloc[0]
                session_metadata = json.loads(metadata_row['file_parameters'])
                print(f"   Last file index: {metadata_row.get('current_file_index', 'Not found')}")
                print(f"   Metadata keys: {list(session_metadata.keys())}")
            except Exception as e:
                print(f"⚠️  Warning: Could not parse session metadata: {e}")
            
            # Remove metadata row for file checking
            df_session = df_session.iloc[1:].reset_index(drop=True)
        else:
            print("ℹ️  No session metadata found (older format)")
        
        # Check file paths
        print(f"\nChecking {len(df_session)} files...")
        existing_files = 0
        missing_files = 0
        
        for i, row in df_session.iterrows():
            file_path = row['local_file_path']
            if os.path.exists(file_path):
                existing_files += 1
            else:
                missing_files += 1
                if missing_files <= 3:  # Show first 3 missing files
                    print(f"   ❌ Missing: {file_path}")
        
        print(f"\nFile Status:")
        print(f"   ✅ Existing files: {existing_files}")
        print(f"   ❌ Missing files: {missing_files}")
        
        # Check bool_good_curve values
        df_session['bool_good_curve'] = pd.to_numeric(df_session['bool_good_curve'], errors='coerce').fillna(0).astype(int)
        good_files = len(df_session[df_session['bool_good_curve'] == 1])
        bad_files = len(df_session[df_session['bool_good_curve'] == 0])
        
        print(f"\nFile Ratings:")
        print(f"   ✅ Good files: {good_files}")
        print(f"   ❌ Bad files: {bad_files}")
        
        # Check for advanced features
        has_file_parameters = 'file_parameters' in df_session.columns
        has_plateau_selections = 'plateau_selections' in df_session.columns
        
        print(f"\nAdvanced Features:")
        print(f"   📊 Per-file parameters: {'✅ Available' if has_file_parameters else '❌ Not available'}")
        print(f"   🎯 Plateau selections: {'✅ Available' if has_plateau_selections else '❌ Not available'}")
        
        if existing_files == 0:
            print(f"\n❌ CRITICAL: No files from session exist on disk!")
            print(f"   The session may have been created on a different computer or")
            print(f"   the files may have been moved/deleted.")
            return False
        
        print(f"\n✅ Session file appears valid!")
        print(f"   {existing_files}/{len(df_session)} files can be loaded")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR loading session file: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 test_session.py <session_file.csv>")
        print("\nExample:")
        print("python3 test_session.py /path/to/tether_session_20250106_123456.csv")
        sys.exit(1)
    
    session_file = sys.argv[1]
    success = test_session_file(session_file)
    
    if not success:
        print(f"\n💡 Suggestions:")
        print(f"   1. Check if the session file was created on this computer")
        print(f"   2. Verify that the TDMS files haven't been moved or deleted")
        print(f"   3. Try loading a smaller subset (good files only)")
        print(f"   4. Check file permissions")
        
        sys.exit(1)
    else:
        print(f"\n🎉 Session file looks good! It should load successfully in the GUI.")
