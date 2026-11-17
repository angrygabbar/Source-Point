import SaveIcon from '@mui/icons-material/Save';
import { Alert, Box, Button, Paper, TextField } from '@mui/material';
import { FormEvent, useState } from 'react';
import { api } from '../api';
import { SectionHeader } from '../components/SectionHeader';
import type { UserProfile } from '../types';

interface ProfileViewProps {
  user: UserProfile;
  onProfileUpdated: (profile: UserProfile) => void;
}

export function ProfileView({ user, onProfileUpdated }: ProfileViewProps) {
  const [form, setForm] = useState({
    name: user.name,
    age: user.age == null ? '' : String(user.age),
    maritalStatus: user.maritalStatus,
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const profile = await api.updateProfile({
        name: form.name,
        age: Number(form.age),
        maritalStatus: form.maritalStatus,
      });
      onProfileUpdated(profile);
      setMessage('Profile updated.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update profile');
    }
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Paper component="form" onSubmit={submit} variant="outlined" sx={{ p: 2 }}>
        <SectionHeader title="User Profile" />
        {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' }, gap: 1.5 }}>
          <TextField
            label="Name"
            value={form.name}
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            required
          />
          <TextField label="Email" value={user.email} disabled />
          <TextField
            label="Age"
            type="number"
            value={form.age}
            onChange={(event) => setForm((current) => ({ ...current, age: event.target.value }))}
            slotProps={{ htmlInput: { min: 18 } }}
            required
          />
          <TextField
            label="Marital Status"
            value={form.maritalStatus}
            onChange={(event) => setForm((current) => ({ ...current, maritalStatus: event.target.value }))}
            required
          />
        </Box>
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button type="submit" variant="contained" startIcon={<SaveIcon />}>
            Save Profile
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}
