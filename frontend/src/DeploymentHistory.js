import React, { useState, useEffect } from 'react';
import { Box, Typography, Table, TableBody, TableCell, TableHead, TableRow, TextField, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import axios from 'axios';

function DeploymentHistory() {
  const [deployments, setDeployments] = useState([]);
  const [serviceFilter, setServiceFilter] = useState('');
  const [envFilter, setEnvFilter] = useState('');

  useEffect(() => {
    const params = {};
    if (serviceFilter) params.service = serviceFilter;
    if (envFilter) params.env = envFilter;
    axios.get('http://localhost:8000/deployments/history', { params })
      .then(res => setDeployments(res.data.deployments));
  }, [serviceFilter, envFilter]);

  return (
    <Box>
      <Typography variant="h5">Deployment History</Typography>
      <FormControl sx={{ m: 1, minWidth: 120 }}>
        <InputLabel>Service</InputLabel>
        <Select value={serviceFilter} onChange={e => setServiceFilter(e.target.value)}>
          <MenuItem value="">All</MenuItem>
          {['contract-api', 'contract-web-admin', 'retail-api', 'retail-web-admin'].map(s => (
            <MenuItem key={s} value={s}>{s}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <FormControl sx={{ m: 1, minWidth: 120 }}>
        <InputLabel>Environment</InputLabel>
        <Select value={envFilter} onChange={e => setEnvFilter(e.target.value)}>
          <MenuItem value="">All</MenuItem>
          <MenuItem value="dev">DEV</MenuItem>
          <MenuItem value="stag">STAG</MenuItem>
          <MenuItem value="prod">PROD</MenuItem>
        </Select>
      </FormControl>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Service</TableCell>
            <TableCell>Env</TableCell>
            <TableCell>Tag</TableCell>
            <TableCell>PR URL</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Created At</TableCell>
            <TableCell>Approved By</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {deployments.map(d => (
            <TableRow key={d.id}>
              <TableCell>{d.service}</TableCell>
              <TableCell>{d.env}</TableCell>
              <TableCell>{d.tag}</TableCell>
              <TableCell><a href={d.pr_url}>{d.pr_url}</a></TableCell>
              <TableCell>{d.status}</TableCell>
              <TableCell>{new Date(d.created_at).toLocaleString()}</TableCell>
              <TableCell>{d.approved_by || '-'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

export default DeploymentHistory;