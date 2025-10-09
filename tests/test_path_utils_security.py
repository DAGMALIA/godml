# test_path_utils_security.py
import pytest
import tempfile
import os
from pathlib import Path
from godml.utils.path_utils import (
    SecurityError, 
    normalize_path, 
    validate_safe_path, 
    safe_join,
    sanitize_for_log
)

class TestPathUtilsSecurity:
    
    def test_normalize_path_secure(self):
        """Test que normalize_path rechaza patrones peligrosos"""
        # Casos válidos
        assert normalize_path("/tmp/test.txt")
        assert normalize_path("./data/file.csv")
        
        # Casos peligrosos - deben fallar
        with pytest.raises(SecurityError, match="Patrón peligroso"):
            normalize_path("../../../etc/passwd")
        
        with pytest.raises(SecurityError, match="Patrón peligroso"):
            normalize_path("~/../../etc/passwd")
            
        with pytest.raises(SecurityError, match="Caracteres de control"):
            normalize_path("/tmp/file\x00.txt")
    
    def test_validate_safe_path_security(self):
        """Test que validate_safe_path previene path traversal"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Casos válidos
            safe_file = Path(tmpdir) / "safe.txt"
            safe_file.touch()
            
            result = validate_safe_path(str(safe_file), tmpdir)
            assert result.exists()
            
            # Casos peligrosos - deben fallar
            with pytest.raises(SecurityError, match="Patrón peligroso"):
                validate_safe_path("../../../etc/passwd", tmpdir)
            
            with pytest.raises(SecurityError, match="fuera del directorio"):
                validate_safe_path("/etc/passwd", tmpdir)
                
            with pytest.raises(SecurityError, match="Caracteres de control"):
                validate_safe_path("/tmp/file\x00.txt", tmpdir)
    
    def test_safe_join_security(self):
        """Test que safe_join previene path traversal"""
        # Casos válidos
        result = safe_join("data", "models", "model.pkl")
        assert "data" in result and "models" in result
        
        # Casos peligrosos - deben fallar
        with pytest.raises(SecurityError, match="peligroso"):
            safe_join("data", "..", "etc", "passwd")
            
        with pytest.raises(SecurityError, match="peligroso"):
            safe_join("data", "/etc/passwd")
            
        with pytest.raises(SecurityError, match="Caracteres de control"):
            safe_join("data", "file\x00.txt")
    
    def test_sanitize_for_log_security(self):
        """Test que sanitize_for_log remueve caracteres peligrosos"""
        # Casos normales
        assert sanitize_for_log("normal text") == "normal text"
        
        # Casos con caracteres peligrosos
        dangerous = "text\nwith\rcontrol\tchars\x00"
        sanitized = sanitize_for_log(dangerous)
        assert "\n" not in sanitized
        assert "\r" not in sanitized
        assert "\t" not in sanitized
        assert "\x00" not in sanitized
        
        # Test de longitud máxima
        long_text = "a" * 600
        sanitized = sanitize_for_log(long_text)
        assert len(sanitized) <= 503  # 500 + "..."

if __name__ == "__main__":
    # Ejecutar tests básicos
    test = TestPathUtilsSecurity()
    
    print("🧪 Ejecutando tests de seguridad path_utils...")
    
    try:
        test.test_normalize_path_secure()
        print("✅ Test normalize_path security: PASSED")
    except Exception as e:
        print(f"❌ Test normalize_path security: FAILED - {e}")
    
    try:
        test.test_validate_safe_path_security()
        print("✅ Test validate_safe_path security: PASSED")
    except Exception as e:
        print(f"❌ Test validate_safe_path security: FAILED - {e}")
    
    try:
        test.test_safe_join_security()
        print("✅ Test safe_join security: PASSED")
    except Exception as e:
        print(f"❌ Test safe_join security: FAILED - {e}")
        
    try:
        test.test_sanitize_for_log_security()
        print("✅ Test sanitize_for_log security: PASSED")
    except Exception as e:
        print(f"❌ Test sanitize_for_log security: FAILED - {e}")
    
    print("🎉 Tests de seguridad completados")
