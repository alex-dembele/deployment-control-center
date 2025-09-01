import React, { useState, useEffect } from 'react';
import { Grid, Card, CardContent, Typography, Button, TextField } from '@mui/material';
import axios from 'axios';

function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [services, setServices] = useState([]);

  const handleLogin = () => {
    axios.post('http://localhost:8000/login', { username, password })
      .then(() => setLoggedIn(true))
      .catch(err => alert('Login failed'));
  };

  useEffect(() => {
    if (loggedIn) {
      axios.get('http://localhost:8000/services')
        .then(res => setServices(res.data.services));
    }
  }, [loggedIn]);

  if (!loggedIn) {
    return (
      <div>
        <TextField label="Username" onChange={e => setUsername(e.target.value)} />
        <TextField label="Password" type="password" onChange={e => setPassword(e.target.value)} />
        <Button onClick={handleLogin}>Login</Button>
      </div>
    );
  }

  return (
    <Grid container spacing={2}>
      {services.map(s => (
        <Grid item xs={4} key={s.name}>
          <Card>
            <CardContent>
              <Typography>{s.name}</Typography>
              <Typography>Envs: {s.envs.join(', ')}</Typography>
              <Button>Déployer</Button>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

export default App;