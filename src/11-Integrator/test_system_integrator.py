import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from system_integrator import SystemIntegrator

@pytest.mark.asyncio
async def test_pipeline_completo_sem_erro():
    # Mocks
    mock_processor = MagicMock()
    mock_processor.processar_palavras.return_value = ["p1", "p2", "p3"]

    mock_api = AsyncMock()
    mock_coletor = MagicMock()
    mock_coletor.coletar.return_value = ["p1", "p2", "p3"]

    with patch("system_integrator.KeywordProcessor", return_value=mock_processor),          patch("system_integrator.APIClient", return_value=mock_api),          patch("system_integrator.GoogleAutocompleteCollector", return_value=mock_coletor),          patch("system_integrator.GoogleTrendsCollector", return_value=mock_coletor),          patch("system_integrator.inserir_multiplas_palavras", new=AsyncMock()):

        integrator = SystemIntegrator(nicho="tecnologia", dry_run=False)
        await integrator.executar_pipeline()

        mock_processor.processar_palavras.assert_called()
        mock_api.enviar_para_api.assert_called()
        mock_api.reenviar_falhas.assert_not_called()  # não chamado diretamente no v2

@pytest.mark.asyncio
async def test_pipeline_com_dry_run():
    integrator = SystemIntegrator(nicho="negocios", dry_run=True)

    with patch.object(integrator, "coletar_dados", return_value=["teste"]),          patch.object(integrator, "processar_dados", return_value=["teste"]),          patch.object(integrator, "armazenar_dados") as mock_store,          patch.object(integrator, "enviar_para_api") as mock_send:
        
        await integrator.executar_pipeline()
        mock_store.assert_called()
        mock_send.assert_called()