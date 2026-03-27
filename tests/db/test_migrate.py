"""
Tests for database migration module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.migrate import (
    get_alembic_config,
    upgrade,
    downgrade,
    current,
    history,
    heads,
    stamp,
    main,
)


class TestGetAlembicConfig:
    """Tests for Alembic config retrieval."""
    
    @patch('src.db.migrate.Config')
    @patch('src.db.migrate.os.environ.get')
    def test_get_alembic_config_default(self, mock_environ, mock_config):
        """Test getting default Alembic config."""
        mock_environ.return_value = None
        
        get_alembic_config()
        
        # Should use default path
        mock_config.assert_called_once()
        call_args = mock_config.call_args[0][0]
        assert 'alembic.ini' in str(call_args)
    
    @patch('src.db.migrate.Config')
    @patch('src.db.migrate.os.environ.get')
    def test_get_alembic_config_custom(self, mock_environ, mock_config):
        """Test getting custom Alembic config."""
        mock_environ.return_value = '/custom/path/alembic.ini'
        
        get_alembic_config()
        
        mock_config.assert_called_once_with('/custom/path/alembic.ini')


class TestUpgrade:
    """Tests for upgrade migration."""
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_upgrade_default(self, mock_get_config, mock_command):
        """Test upgrade to head."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        upgrade()
        
        mock_command.upgrade.assert_called_once_with(mock_config, 'head')
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_upgrade_specific_revision(self, mock_get_config, mock_command):
        """Test upgrade to specific revision."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        upgrade('001_initial')
        
        mock_command.upgrade.assert_called_once_with(mock_config, '001_initial')


class TestDowngrade:
    """Tests for downgrade migration."""
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_downgrade_default(self, mock_get_config, mock_command):
        """Test default downgrade (one step)."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        downgrade()
        
        mock_command.downgrade.assert_called_once_with(mock_config, '-1')
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_downgrade_to_base(self, mock_get_config, mock_command):
        """Test downgrade to base."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        downgrade('base')
        
        mock_command.downgrade.assert_called_once_with(mock_config, 'base')
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_downgrade_specific_revision(self, mock_get_config, mock_command):
        """Test downgrade to specific revision."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        downgrade('001_initial')
        
        mock_command.downgrade.assert_called_once_with(mock_config, '001_initial')


class TestCurrent:
    """Tests for current version check."""
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_current(self, mock_get_config, mock_command):
        """Test getting current migration version."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        current()
        
        mock_command.current.assert_called_once_with(mock_config)


class TestHistory:
    """Tests for migration history."""
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_history(self, mock_get_config, mock_command):
        """Test getting migration history."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        history()
        
        mock_command.history.assert_called_once_with(mock_config)


class TestHeads:
    """Tests for available heads."""
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_heads(self, mock_get_config, mock_command):
        """Test getting available head revisions."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        heads()
        
        mock_command.heads.assert_called_once_with(mock_config)


class TestStamp:
    """Tests for stamp command."""
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_stamp(self, mock_get_config, mock_command):
        """Test stamping database at revision."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        stamp('001_initial')
        
        mock_command.stamp.assert_called_once_with(mock_config, '001_initial')


class TestMain:
    """Tests for main CLI entry point."""
    
    @patch('src.db.migrate.upgrade')
    @patch('src.db.migrate.sys.argv', ['migrate.py', 'upgrade'])
    def test_main_upgrade(self, mock_upgrade):
        """Test main with upgrade command."""
        main()
        
        mock_upgrade.assert_called_once()
    
    @patch('src.db.migrate.downgrade')
    @patch('src.db.migrate.sys.argv', ['migrate.py', 'downgrade'])
    def test_main_downgrade(self, mock_downgrade):
        """Test main with downgrade command."""
        main()
        
        mock_downgrade.assert_called_once()
    
    @patch('src.db.migrate.current')
    @patch('src.db.migrate.sys.argv', ['migrate.py', 'current'])
    def test_main_current(self, mock_current):
        """Test main with current command."""
        main()
        
        mock_current.assert_called_once()
    
    @patch('src.db.migrate.history')
    @patch('src.db.migrate.sys.argv', ['migrate.py', 'history'])
    def test_main_history(self, mock_history):
        """Test main with history command."""
        main()
        
        mock_history.assert_called_once()
    
    @patch('src.db.migrate.heads')
    @patch('src.db.migrate.sys.argv', ['migrate.py', 'heads'])
    def test_main_heads(self, mock_heads):
        """Test main with heads command."""
        main()
        
        mock_heads.assert_called_once()
    
    @patch('src.db.migrate.stamp')
    @patch('src.db.migrate.sys.argv', ['migrate.py', 'stamp', '001_initial'])
    def test_main_stamp(self, mock_stamp):
        """Test main with stamp command."""
        main()
        
        mock_stamp.assert_called_once_with('001_initial')
    
    @patch('src.db.migrate.print')
    @patch('src.db.migrate.sys.argv', ['migrate.py', 'invalid'])
    def test_main_invalid_command(self, mock_print):
        """Test main with invalid command."""
        main()
        
        mock_print.assert_called()
        assert 'Invalid' in str(mock_print.call_args)
    
    @patch('src.db.migrate.print')
    @patch('src.db.migrate.sys.argv', ['migrate.py'])
    def test_main_no_command(self, mock_print):
        """Test main with no command."""
        main()
        
        mock_print.assert_called()
        assert 'usage' in str(mock_print.call_args).lower()


class TestMigrationErrorHandling:
    """Tests for migration error handling."""
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_upgrade_error(self, mock_get_config, mock_command):
        """Test upgrade with Alembic error."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        mock_command.upgrade.side_effect = Exception("Migration failed")
        
        with pytest.raises(Exception):
            upgrade()
    
    @patch('src.db.migrate.command')
    @patch('src.db.migrate.get_alembic_config')
    def test_downgrade_error(self, mock_get_config, mock_command):
        """Test downgrade with Alembic error."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        mock_command.downgrade.side_effect = Exception("Downgrade failed")
        
        with pytest.raises(Exception):
            downgrade()
