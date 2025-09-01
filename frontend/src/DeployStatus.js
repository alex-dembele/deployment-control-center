import React, { useState, useEffect } from 'react';
import { Box, Typography } from '@mui/material';
import axios from 'axios';
import Mermaid from 'mermaid';

function DeployStatus({ prUrl, deployId }) {
  const [status, setStatus] = useState('pending');
  const prId = prUrl.split('/').pop();

  useEffect(() => {
    Mermaid.initialize({ startOnLoad: true });
    const interval = setInterval(() => {
      axios.get(`http://localhost:8000/pr-status/${prId}`)
        .then(res => setStatus(res.data.merged ? 'merged' : res.data.status));
      if (deployId) {
        axios.get(`http://localhost:8000/deployments/${deployId}`)
          .then(res => setStatus(res.data.status));
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [prId, deployId]);

  const mermaidDiagram = `
    graph TD
      A[Utilisateur: Clique Déployer] --> B[Backend: Valide]
      B --> C[Git: PR Créée]
      C --> D{Attente Validation?}
      D -->|${status === 'pending' ? 'Oui' : 'Non'}| E[${status === 'pending' ? 'Bloqué PR' : status === 'approved' ? 'Approved' : status === 'merged' ? 'Merged' : 'Rejected'}]
      E --> F[Argo CD Sync]
  `;

  return (
    <Box>
      <Typography>Deployment Status: {status}</Typography>
      <div className="mermaid">{mermaidDiagram}</div>
    </Box>
  );
}

export default DeployStatus;