#!/usr/bin/env python3
"""
Test script to verify the new Butterworth wavelengths parameter format
"""

# Test the parameter conversion logic
def test_butterworth_conversion():
    """Test wavelength to wavenumber conversion for Butterworth parameters"""
    
    def wavelength_to_wavenumber(wavelength_um):
        """Convert wavelength in micrometers to wavenumber in µm⁻¹"""
        return 1.0 / wavelength_um
    
    # Test input: butterworth_wavelengths = "[(0.25, 10.0)]"
    import ast
    
    butterworth_wavelengths_str = "[(0.25, 10.0)]"
    print(f"Input: butterworth_wavelengths = {butterworth_wavelengths_str}")
    
    try:
        wavelength_ranges = ast.literal_eval(butterworth_wavelengths_str)
        wavenumber_ranges = []
        
        for wl_range in wavelength_ranges:
            if len(wl_range) == 2:
                # Note: order reversal because wavelength and wavenumber are inversely related
                wn_low = wavelength_to_wavenumber(wl_range[1])   # Higher wavelength → lower wavenumber (W0)
                wn_high = wavelength_to_wavenumber(wl_range[0])  # Lower wavelength → higher wavenumber (W1)
                wavenumber_ranges.append((wn_low, wn_high))
        
        # For now, use the first range for w0 and w1 (backward compatibility)
        if wavenumber_ranges:
            denoise_w0 = wavenumber_ranges[0][0]  # Lower wavenumber
            denoise_w1 = wavenumber_ranges[0][1]  # Higher wavenumber
            
            print(f"Converted: denoise_w0 = {denoise_w0:.3f} µm⁻¹ (from {wl_range[1]} µm)")
            print(f"Converted: denoise_w1 = {denoise_w1:.3f} µm⁻¹ (from {wl_range[0]} µm)")
            
            # Test reverse conversion
            def wavenumber_to_wavelength(wavenumber_um_inv):
                """Convert wavenumber in µm⁻¹ to wavelength in micrometers"""
                return 1.0 / wavenumber_um_inv
            
            wl_max = wavenumber_to_wavelength(denoise_w0)  # W0 -> max wavelength
            wl_min = wavenumber_to_wavelength(denoise_w1)  # W1 -> min wavelength
            
            # Format as array string
            wavelength_ranges_back = [(wl_min, wl_max)]
            print(f"Reverse converted: {wavelength_ranges_back}")
            print(f"Original input:   {wavelength_ranges}")
            
            # Check if they match (within floating point precision)
            original = wavelength_ranges[0]
            converted_back = wavelength_ranges_back[0]
            
            if abs(original[0] - converted_back[0]) < 0.001 and abs(original[1] - converted_back[1]) < 0.001:
                print("✅ Conversion test PASSED - round trip successful!")
            else:
                print("❌ Conversion test FAILED - round trip error!")
                
        else:
            print("❌ No wavelength ranges found")
            
    except Exception as e:
        print(f"❌ Error in conversion: {e}")

if __name__ == "__main__":
    test_butterworth_conversion()
