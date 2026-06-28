# test_model_loader_secure.py
import pytest
import pandas as pd
import numpy as np
from godml.model_service.model_loader import load_custom_model_class, register_adhoc_model
from godml.model_service.base_model_interface import BaseModel
from godml.monitoring_service.logger import SecurityError, ModelLoadError

class TestModelLoaderSecure:
    
    def test_load_core_model_xgboost(self):
        """Test carga segura de modelo core XGBoost"""
        model = load_custom_model_class("./", "xgboost", source="core")
        assert model is not None
        assert isinstance(model, BaseModel)
    
    def test_load_core_model_random_forest(self):
        """Test carga segura de modelo core Random Forest"""
        model = load_custom_model_class("./", "random_forest", source="core")
        assert model is not None
        assert isinstance(model, BaseModel)
    
    def test_load_core_model_linear_regression(self):
        """Test carga segura de modelo core Linear Regression"""
        model = load_custom_model_class("./", "linear_regression", source="core")
        assert model is not None
        assert isinstance(model, BaseModel)
        
        # Test funcionalidad básica
        X_train = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [10, 20, 30]})
        y_train = np.array([15, 30, 45])
        X_test = pd.DataFrame({"feature1": [4], "feature2": [40]})
        y_test = np.array([60])
        
        trained_model, predictions, metrics = model.train(X_train, y_train, X_test, y_test, {})
        assert trained_model is not None
        assert predictions is not None
        assert isinstance(metrics, dict)
    
    def test_adhoc_model_registration(self):
        """Test registro y carga de modelo ad-hoc"""
        
        # Crear modelo ad-hoc de prueba
        class TestModel(BaseModel):
            def train(self, X_train, y_train, X_test, y_test, params):
                return "mock_model", np.array([1, 2, 3]), {"accuracy": 0.95}
            
            def predict(self, X):
                return np.array([1] * len(X))
        
        # Registrar modelo
        register_adhoc_model("test_model", TestModel)
        
        # Cargar modelo registrado
        model = load_custom_model_class("./", "test_model", source="adhoc")
        assert model is not None
        assert isinstance(model, BaseModel)
    
    def test_adhoc_model_direct_class(self):
        """Test carga directa de clase ad-hoc"""
        
        class DirectModel(BaseModel):
            def train(self, X_train, y_train, X_test, y_test, params):
                return "mock_model", np.array([1, 2]), {"accuracy": 0.90}
            
            def predict(self, X):
                return np.array([0] * len(X))
        
        # Cargar clase directamente
        model = load_custom_model_class("./", "direct_model", source="adhoc", adhoc_model_class=DirectModel)
        assert model is not None
        assert isinstance(model, BaseModel)
    
    def test_security_invalid_model_type(self):
        """Test validación de seguridad - tipo de modelo inválido"""
        with pytest.raises(SecurityError):
            load_custom_model_class("./", "invalid-model!", source="core")
    
    def test_security_invalid_source(self):
        """Test validación de seguridad - source inválido"""
        with pytest.raises(SecurityError):
            load_custom_model_class("./", "xgboost", source="local")  # local deshabilitado
    
    def test_security_nonexistent_core_model(self):
        """Test validación de seguridad - modelo core inexistente"""
        with pytest.raises(SecurityError):
            load_custom_model_class("./", "nonexistent_model", source="core")
    
    def test_security_unregistered_adhoc_model(self):
        """Test validación de seguridad - modelo ad-hoc no registrado"""
        with pytest.raises(ModelLoadError):
            load_custom_model_class("./", "unregistered_model", source="adhoc")
    
    def test_security_invalid_adhoc_class(self):
        """Test validación de seguridad - clase ad-hoc inválida"""
        
        class InvalidModel:  # No hereda de BaseModel
            pass
        
        with pytest.raises(SecurityError):
            load_custom_model_class("./", "invalid", source="adhoc", adhoc_model_class=InvalidModel)

if __name__ == "__main__":
    # Ejecutar tests básicos
    test = TestModelLoaderSecure()
    
    print("🧪 Ejecutando tests de model_loader seguro...")
    
    try:
        test.test_load_core_model_linear_regression()
        print("✅ Test core linear_regression: PASSED")
    except Exception as e:
        print(f"❌ Test core linear_regression: FAILED - {e}")
    
    try:
        test.test_adhoc_model_registration()
        print("✅ Test adhoc registration: PASSED")
    except Exception as e:
        print(f"❌ Test adhoc registration: FAILED - {e}")
    
    try:
        test.test_security_invalid_model_type()
        print("✅ Test security validation: PASSED")
    except Exception as e:
        print(f"❌ Test security validation: FAILED - {e}")
    
    print("🎉 Tests completados")
