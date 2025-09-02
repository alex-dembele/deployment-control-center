import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Paper,
  Grid,
  useTheme
} from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useSnackbar } from 'notistack';
import { useTranslation } from 'react-i18next';
import axios from 'axios';

function DeploymentHistory() {
  const { t } = useTranslation();
  const theme = useTheme();
  const { enqueueSnackbar } = useSnackbar();
  const [deployments, setDeployments] = useState([]);
  const [serviceFilter, setServiceFilter] = useState('');
  const [envFilter, setEnvFilter] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [perPage] = useState(10);
  const [loading, setLoading] = useState(false);
  const [services, setServices] = useState([]);

  // Fetch services for filter dropdown
  useEffect(() => {
    axios.get('http://localhost:8000/services')
      .then(res => setServices(res.data.services))
      .catch(() => enqueueSnackbar(t('error.servicesFetch'), { variant: 'error' }));
  }, [t, enqueueSnackbar]);

  // Fetch deployment history
  useEffect(() => {
    setLoading(true);
    const params = { page, per_page: perPage };
    if (serviceFilter) params.service = serviceFilter;
    if (envFilter) params.env = envFilter;
    axios.get('http://localhost:8000/deployments/history', { params })
      .then(res => {
        setDeployments(res.data.deployments);
        setTotal(res.data.total);
      })
      .catch(err => {
        enqueueSnackbar(t('error.historyFetch'), { variant: 'error' });
        console.error(err);
      })
      .finally(() => setLoading(false));
  }, [serviceFilter, envFilter, page, t, enqueueSnackbar]);

  // Prepare data for chart
  const chartData = services.map(service => ({
    name: service.name,
    count: deployments.filter(d => d.service === service.name).length
  }));

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: '1200px', mx: 'auto' }} role="region" aria-label={t('deploymentHistory')}>
      <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 'bold' }}>
        {t('deploymentHistory')}
      </Typography>

      {/* Filters */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={4}>
          <FormControl fullWidth>
            <InputLabel id="service-filter-label">{t('service')}</InputLabel>
            <Select
              labelId="service-filter-label"
              value={serviceFilter}
              label={t('service')}
              onChange={e => setServiceFilter(e.target.value)}
              aria-describedby="service-filter-help"
            >
              <MenuItem value="">{t('all')}</MenuItem>
              {services.map(s => (
                <MenuItem key={s.name} value={s.name}>{s.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <FormControl fullWidth>
            <InputLabel id="env-filter-label">{t('environment')}</InputLabel>
            <Select
              labelId="env-filter-label"
              value={envFilter}
              label={t('environment')}
              onChange={e => setEnvFilter(e.target.value)}
              aria-describedby="env-filter-help"
            >
              <MenuItem value="">{t('all')}</MenuItem>
              <MenuItem value="dev">{t('dev')}</MenuItem>
              <MenuItem value="stag">{t('stag')}</MenuItem>
              <MenuItem value="prod">{t('prod')}</MenuItem>
            </Select>
          </FormControl>
        </Grid>
      </Grid>

      {/* Metrics Chart */}
      <Paper sx={{ p: 2, mb: 3 }} elevation={3}>
        <Typography variant="h6" gutterBottom>{t('deploymentsByService')}</Typography>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill={theme.palette.primary.main} />
          </BarChart>
        </ResponsiveContainer>
      </Paper>

      {/* Deployment Table */}
      <Paper elevation={3}>
        <Table aria-label={t('deploymentTable')}>
          <TableHead>
            <TableRow>
              <TableCell>{t('service')}</TableCell>
              <TableCell>{t('environment')}</TableCell>
              <TableCell>{t('tag')}</TableCell>
              <TableCell>{t('prUrl')}</TableCell>
              <TableCell>{t('status')}</TableCell>
              <TableCell>{t('createdAt')}</TableCell>
              <TableCell>{t('approvedBy')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={7} align="center">{t('loading')}</TableCell>
              </TableRow>
            ) : deployments.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">{t('noDeployments')}</TableCell>
              </TableRow>
            ) : (
              deployments.map(d => (
                <TableRow key={d.id}>
                  <TableCell>{d.service}</TableCell>
                  <TableCell>{d.env}</TableCell>
                  <TableCell>{d.tag}</TableCell>
                  <TableCell>
                    <a href={d.pr_url} target="_blank" rel="noopener noreferrer" aria-label={t('prLink')}>
                      {d.pr_url.split('/').pop()}
                    </a>
                  </TableCell>
                  <TableCell>{t(d.status)}</TableCell>
                  <TableCell>{new Date(d.created_at).toLocaleString()}</TableCell>
                  <TableCell>{d.approved_by || '-'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Paper>

      {/* Pagination */}
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Button
          disabled={page === 1 || loading}
          onClick={() => setPage(page - 1)}
          aria-label={t('previousPage')}
        >
          {t('previous')}
        </Button>
        <Typography sx={{ mx: 2 }}>
          {t('page')} {page} {t('of')} {Math.ceil(total / perPage)}
        </Typography>
        <Button
          disabled={page * perPage >= total || loading}
          onClick={() => setPage(page + 1)}
          aria-label={t('nextPage')}
        >
          {t('next')}
        </Button>
      </Box>
    </Box>
  );
}

export default DeploymentHistory;