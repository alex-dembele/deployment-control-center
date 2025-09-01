import React, { useEffect, useState } from 'react';
import { Grid, Card, CardContent, Typography, Button } from '@mui/material';
import axios from 'axios';  // Ajoute à package.json

function App() {
  const [services, setServices] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8000/services')  // TODO: Impl endpoint
      .then(res => setServices(res.data));
  }, []);

  return (
    <Grid container spacing={2}>
      {services.map(s => (
        <Grid item xs={4} key={s.name}>
          <Card>
            <CardContent>
              <Typography>{s.name}</Typography>
              <Button>Déployer</Button>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

export default App;