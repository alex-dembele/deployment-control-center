import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';
import axios from 'axios';

function Approvals() {
  const [deployments, setDeployments] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8000/deployments').then(res => setDeployments(res.data.deployments));
  }, []);

  const handleApprove = (id, approved) => {
    axios.post('http://localhost:8000/approve', { deploy_id: id, approved })
      .then(() => setDeployments(deployments.filter(d => d.id !== id)));
  };

  return (
    <Box>
      <Typography variant="h5">Pending Approvals</Typography>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Service</TableCell>
            <TableCell>Env</TableCell>
            <TableCell>Tag</TableCell>
            <TableCell>PR URL</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {deployments.map(d => (
            <TableRow key={d.id}>
              <TableCell>{d.service}</TableCell>
              <TableCell>{d.env}</TableCell>
              <TableCell>{d.tag}</TableCell>
              <TableCell><a href={d.pr_url}>{d.pr_url}</a></TableCell>
              <TableCell>
                <Button onClick={() => handleApprove(d.id, true)}>Approve</Button>
                <Button onClick={() => handleApprove(d.id, false)}>Reject</Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
}

export default Approvals;