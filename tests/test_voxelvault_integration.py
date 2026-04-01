"""Tests for VoxelVault integration plugin."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tkinter as tk

from tkgis.plugins.builtin.voxelvault_provider import VoxelVaultDataProvider, VoxelVaultPlugin
from tkgis.plugins.base import PluginContext
from tkgis.models.project import Project

class TestVoxelVaultIntegration:
    def test_provider_name(self):
        provider = VoxelVaultDataProvider()
        assert provider.name == "voxelvault"

    def test_can_open_vault(self, tmp_path):
        vault_dir = tmp_path / "my_vault"
        vault_dir.mkdir()
        (vault_dir / "v2.db").touch()
        (vault_dir / "vault.json").touch()
        
        provider = VoxelVaultDataProvider()
        assert provider.can_open(vault_dir) is True
        assert provider.can_open(vault_dir / "v2.db") is True

    def test_plugin_activation(self):
        ctx = PluginContext()
        ctx.register_data_provider = MagicMock()
        ctx.add_menu_item = MagicMock()
        
        plugin = VoxelVaultPlugin()
        plugin.activate(ctx)
        
        ctx.register_data_provider.assert_called_once()
        ctx.add_menu_item.assert_called_with("Layer", "Export to VoxelVault...", plugin._on_export_to_vault)

    @patch("tkgis.plugins.builtin.voxelvault_provider.Vault.open")
    @patch("tkgis.plugins.builtin.voxelvault_provider.VoxelVaultQueryDialog")
    def test_open_vault_cancels(self, mock_dialog_cls, mock_vault_open, tmp_path):
        vault_dir = tmp_path / "my_vault"
        vault_dir.mkdir()
        (vault_dir / "v2.db").touch()
        (vault_dir / "vault.json").touch()
        
        mock_vault = MagicMock()
        mock_vault_open.return_value = mock_vault
        
        mock_dialog = MagicMock()
        mock_dialog.result = None
        mock_dialog_cls.return_value = mock_dialog
        
        provider = VoxelVaultDataProvider()
        # Mock tk._default_root for test
        with patch("tkinter._default_root", tk.Tk()):
            layer = provider.open(vault_dir)
            
        assert layer is None
        mock_vault.close.assert_called_once()
