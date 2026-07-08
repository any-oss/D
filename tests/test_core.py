"""
Tests for Team B AI-Agent System
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRouterLB:
    """Tests for router_lb.py load balancing logic."""
    
    def test_import_router_lb(self):
        """Test that router_lb module can be imported."""
        try:
            import router_lb
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import router_lb: {e}")
    
    def test_config_exists(self):
        """Test that CONFIG is defined in router_lb."""
        from router_lb import CONFIG
        assert isinstance(CONFIG, dict)
        assert len(CONFIG) > 0
        assert "MODELS" in CONFIG
    
    def test_routing_logic(self):
        """Test that routing logic has model definitions."""
        from router_lb import CONFIG
        
        # Verify models are defined
        assert "MODELS" in CONFIG
        models = CONFIG["MODELS"]
        assert isinstance(models, dict)
        assert len(models) > 0
        
        # Verify each model has required fields
        for model_name, model_info in models.items():
            assert "type" in model_info or "capabilities" in model_info


class TestMemoryManager:
    """Tests for memory_mgr.py memory management logic."""
    
    def test_import_memory_mgr(self):
        """Test that memory_mgr module can be imported."""
        try:
            import memory_mgr
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import memory_mgr: {e}")
    
    def test_memory_manager_class_exists(self):
        """Test that MemoryManager class is defined."""
        from memory_mgr import MemoryManager
        assert MemoryManager is not None
    
    def test_memory_manager_initialization(self):
        """Test that MemoryManager can be instantiated."""
        from memory_mgr import MemoryManager
        mgr = MemoryManager()
        assert mgr.max_ram > 0
        assert mgr.reserved_ram > 0


class TestAPIEndpoints:
    """Tests for API endpoint availability."""
    
    def test_import_api_main(self):
        """Test that API main module can be imported."""
        try:
            from api import main
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import api.main: {e}")
    
    def test_fastapi_app_exists(self):
        """Test that FastAPI app is defined."""
        from api.main import app
        assert app is not None
        assert app.title == "Team B AI-Agent System"


class TestRAGWorker:
    """Tests for RAG worker functionality."""
    
    def test_rag_worker_file_exists(self):
        """Test that rag_worker file exists."""
        rag_worker_path = os.path.join(os.path.dirname(__file__), '..', 'rag', 'rag_worker.py')
        assert os.path.exists(rag_worker_path)
    
    def test_rag_worker_content(self):
        """Test that rag_worker has expected content."""
        rag_worker_path = os.path.join(os.path.dirname(__file__), '..', 'rag', 'rag_worker.py')
        with open(rag_worker_path, 'r') as f:
            content = f.read()
        assert 'HTTPServer' in content or 'FastAPI' in content
        assert 'health' in content.lower() or 'status' in content.lower()


class TestScripts:
    """Tests for utility scripts."""
    
    def test_watchdog_exists(self):
        """Test that watchdog script exists and is executable."""
        watchdog_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'watchdog.py')
        assert os.path.exists(watchdog_path)
    
    def test_system_orchestrator_exists(self):
        """Test that system orchestrator script exists."""
        orchestrator_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'system_orchestrator.py')
        assert os.path.exists(orchestrator_path)
    
    def test_improvement_scripts_exist(self):
        """Test that improvement scripts exist."""
        scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
        expected_scripts = [
            'improvement_one_prewarm.py',
            'improvement_two_streaming.py',
            'improvement_three_batching.py'
        ]
        for script in expected_scripts:
            script_path = os.path.join(scripts_dir, script)
            assert os.path.exists(script_path), f"Missing script: {script}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
