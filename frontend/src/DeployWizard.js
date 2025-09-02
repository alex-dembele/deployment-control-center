import React, { useState, useEffect } from 'react';
import { Button, TextField, Select, MenuItem, FormControl, InputLabel, Box, Typography, Checkbox, ListItemText } from '@mui/material';
import axios from 'axios';

function DeployWizard({ onClose }) {
  const [step, setStep] = useState(1);
  const [services, setServices] = useState([]);
  const [form, setForm] = useState({
    service: '',
    tag: '',
    env: 'dev',
    namespace_type: 'internal',
    vars: {},
    secrets: []
  });
  const [envKeys, setEnvKeys] = useState([]);
  const [tags, setTags] = useState([]);
  const [customVars, setCustomVars] = useState([]); 

  useEffect(() => {
    axios.get('http://localhost:8000/services').then(res => setServices(res.data.services));
  }, []);

  useEffect(() => {
    if (form.service) {
      axios.get(`http://localhost:8000/service-env-keys/${form.service}`)
        .then(res => {
          setEnvKeys(res.data.keys);
          setForm(f => ({ ...f, vars: res.data.keys.reduce((acc, key) => ({ ...acc, [key]: '' }), {}) }));
        }).catch(() => {
          setEnvKeys([]);  
        });
      axios.get(`http://localhost:8000/suggest-tags/nexah/${form.service}`)
        .then(res => setTags(res.data.tags || []));
    }
  }, [form.service]);

  const addCustomVar = () => {
    const newKey = prompt('Enter new var key (e.g., MY_VAR):');
    if (newKey) {
      setCustomVars([...customVars, newKey]);
      setForm(f => ({ ...f, vars: { ...f.vars, [newKey]: '' } }));
    }
  };

  const handleNext = () => {
    if (step === 1 && form.service && form.tag && form.env) setStep(2);
    if (step === 2) setStep(3);
    if (step === 3) {
      axios.post('http://localhost:8000/deploy', form)
        .then(res => alert(`PR created: ${res.data.pr_url}`))
        .then(onClose);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {step === 1 && (
        <>
          <FormControl fullWidth>
            <InputLabel>Service</InputLabel>
            <Select value={form.service} onChange={e => setForm({ ...form, service: e.target.value })}>
              {services.map(s => <MenuItem key={s.name} value={s.name}>{s.name}</MenuItem>)}
              <MenuItem value="custom">Custom Project</MenuItem>  // Option pour custom
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Tag</InputLabel>
            <Select value={form.tag} onChange={e => setForm({ ...form, tag: e.target.value })}>
              {tags.map(t => <MenuItem key={t} value={t}>{t}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Environment</InputLabel>
            <Select value={form.env} onChange={e => setForm({ ...form, env: e.target.value })}>
              <MenuItem value="dev">DEV</MenuItem>
              <MenuItem value="stag">STAG</MenuItem>
              <MenuItem value="prod">PROD</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Namespace Type</InputLabel>
            <Select value={form.namespace_type} onChange={e => setForm({ ...form, namespace_type: e.target.value })}>
              <MenuItem value="internal">Internal</MenuItem>
              <MenuItem value="external">External</MenuItem>
            </Select>
          </FormControl>
        </>
      )}
      {step === 2 && (
        <>
          <Typography>Environment Variables</Typography>
          {envKeys.concat(customVars).map(key => (
            <Box key={key}>
              <TextField
                label={key}
                type={form.secrets.includes(key) ? 'password' : 'text'}
                value={form.vars[key] || ''}
                onChange={e => setForm({ ...form, vars: { ...form.vars, [key]: e.target.value } })}
              />
              <Checkbox
                checked={form.secrets.includes(key)}
                onChange={() => setForm({ ...form, secrets: form.secrets.includes(key) ? form.secrets.filter(k => k !== key) : [...form.secrets, key] })}
              />
              <ListItemText primary="Secret" />
            </Box>
          ))}
          <Button onClick={addCustomVar}>Add Custom Var</Button>  // Pour custom projects
        </>
      )}
      {step === 3 && (
        <>
          <Typography>Summary</Typography>
          <Typography>Service: {form.service}</Typography>
          <Typography>Tag: {form.tag}</Typography>
          <Typography>Environment: {form.env}</Typography>
          <Typography>Namespace: {form.namespace_type}</Typography>
          <Typography>Variables: {JSON.stringify(form.vars)}</Typography>
          <Typography>Secrets: {form.secrets.join(', ')}</Typography>
        </>
      )}
      <Button onClick={handleNext}>{step === 3 ? 'Deploy' : 'Next'}</Button>
      {step > 1 && <Button onClick={() => setStep(step - 1)}>Previous</Button>}
      <Button onClick={onClose}>Cancel</Button>
    </Box>
  );
}

export default DeployWizard;