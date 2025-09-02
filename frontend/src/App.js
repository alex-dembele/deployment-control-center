import React, { useState, useEffect, createContext, useMemo } from 'react';
import { Grid, Card, CardContent, Typography, Button, TextField, Modal, Tabs, Tab, Box, createTheme, ThemeProvider, useMediaQuery } from '@mui/material';
import axios from 'axios';
import DeployWizard from './DeployWizard';
import Approvals from './Approvals';
import DeploymentHistory from './DeploymentHistory';
import { SnackbarProvider } from 'notistack';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n.use(initReactI18next).use(LanguageDetector).init({
  resources: {
    en: { translation: { "welcome": "Welcome", "login": "Login", "username": "Username", "password": "Password", "newDeployment": "New Deployment", "services": "Services", "approvals": "Approvals", "history": "History", "deploy": "Deploy", "envs": "Envs" } },
    fr: { translation: { "welcome": "Bienvenue", "login": "Se connecter", "username": "Nom d'utilisateur", "password": "Mot de passe", "newDeployment": "Nouveau Déploiement", "services": "Services", "approvals": "Approbations", "history": "Historique", "deploy": "Déployer", "envs": "Envs" } }
  },
  fallbackLng: "en"
});

export const AuthContext = createContext(null);

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [services, setServices] = useState([]);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [tab, setTab] = useState(0);
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
  const [darkMode, setDarkMode] = useState(prefersDarkMode);

  const handleLogin = () => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    axios.post('http://localhost:8000/token', formData, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
      .then(res => {
        localStorage.setItem('token', res.data.access_token);
        setToken(res.data.access_token);
      })
      .catch(err => alert('Login failed'));
  };

  useEffect(() => {
    if (token) {
      axios.get('http://localhost:8000/services')
        .then(res => setServices(res.data.services));
    }
  }, [token]);

  axios.interceptors.request.use(config => {
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });

  const theme = useMemo(() => createTheme({
    palette: { mode: darkMode ? 'dark' : 'light' }
  }), [darkMode]);

  if (!token) {
    return (
      <ThemeProvider theme={theme}>
        <div>
          <TextField label={i18n.t('username')} onChange={e => setUsername(e.target.value)} />
          <TextField label={i18n.t('password')} type="password" onChange={e => setPassword(e.target.value)} />
          <Button onClick={handleLogin}>{i18n.t('login')}</Button>
        </div>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <SnackbarProvider maxSnack={3}>
        <Button onClick={() => setDarkMode(!darkMode)}>Toggle Theme</Button>
        <Typography>{i18n.t('welcome')}</Typography>
        <Button onClick={() => setWizardOpen(true)}>{i18n.t('newDeployment')}</Button>
        <Tabs value={tab} onChange={(e, newValue) => setTab(newValue)}>
          <Tab label={i18n.t('services')} />
          <Tab label={i18n.t('approvals')} />
          <Tab label={i18n.t('history')} />
        </Tabs>
        {tab === 0 && (
          <Grid container spacing={2}>
            {services.map(s => (
              <Grid item xs={12} sm={6} md={4} key={s.name}>
                <Card>
                  <CardContent>
                    <Typography>{s.name}</Typography>
                    <Typography>{i18n.t('envs')}: {s.envs.join(', ')}</Typography>
                    <Button onClick={() => setWizardOpen(true)}>{i18n.t('deploy')}</Button>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
        {tab === 1 && <Approvals />}
        {tab === 2 && <DeploymentHistory />}
        <Modal open={wizardOpen} onClose={() => setWizardOpen(false)}>
          <Box sx={{ bgcolor: 'background.paper', p: 4, maxWidth: 600, margin: 'auto', mt: 10 }}>
            <DeployWizard onClose={() => setWizardOpen(false)} />
          </Box>
        </Modal>
      </SnackbarProvider>
    </ThemeProvider>
  );
}

export default App;