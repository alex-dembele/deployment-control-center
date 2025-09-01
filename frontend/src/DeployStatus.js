import React, { useState, useEffect } from 'react';
import { Box, Typography } from '@mui/material';
import Mermaid from 'mermaid';

function DeployStatus({ prUrl, deployId }) {
  const [status, setStatus] = useState('pending');
  const [deployStatus, setDeployStatus] = useState('pending');

  useEffect(() => {
    Mermaid.initialize({ startOnLoad: true });
    const ws = new WebSocket(`ws://localhost:8000/ws/pr-status/${deployId}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        setStatus('error');
        setDeployStatus('error');
      } else {
        setStatus(data.merged ? 'merged' : data.status);
        setDeployStatus(data.deploy_status);
      }
    };
    ws.onclose = () => {
      console.log('WebSocket closed, attempting to reconnect...');
      setTimeout(() => {
        window.location.reload(); // Reconnect simpliste
      }, 5000);
    };
    return () => ws.close();
  }, [deployId]);

  const mermaidDiagram = `
    graph TD
      A[Utilisateur: Clique Déployer] --> B[Backend: Valide]
      B --> C[Git: PR Créée]
      C --> D{Attente Validation?}
      D -->|${deployStatus === 'pending' ? 'Oui' : 'Non'}| E[${deployStatus === 'pending' ? 'Bloqué PR' : deployStatus === 'approved' ? 'Approved' : deployStatus === 'merged' ? 'Merged' : 'Rejected'}]
      E --> F[Argo CD Sync]
  `;

  return (
    <Box>
      <Typography>Deployment Status: {deployStatus}</Typography>
      <Typography>PR Status: {status}</Typography>
      <div className="mermaid">{mermaidDiagram}</div>
    </Box>
  );
}

export default DeployStatus;