import { useEffect, useState } from "react";
import {
  Button,
  Checkbox,
  FormControlLabel,
  MenuItem,
  Paper,
  Slider,
  Snackbar,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import { getPolicyRules, savePolicyRules, type PolicyRule, type PolicyRules } from "../services/apiClient";

function extractErrorMessage(err: unknown): string {
  const maybeAxiosErr = err as { response?: { data?: { error?: string } } } | undefined;
  return maybeAxiosErr?.response?.data?.error ?? "Something went wrong. Please try again.";
}

export function PolicyManager() {
  const [rules, setRules] = useState<PolicyRules | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPolicyRules()
      .then(setRules)
      .catch((err) => setError(extractErrorMessage(err)));
  }, []);

  function updateRule(index: number, patch: Partial<PolicyRule>) {
    if (!rules) return;
    const nextRules = rules.rules.map((rule, i) => (i === index ? { ...rule, ...patch } : rule));
    setRules({ ...rules, rules: nextRules });
  }

  async function handleSave() {
    if (!rules) return;
    try {
      await savePolicyRules(rules);
      setSaved(true);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  if (error && !rules) return <Typography color="error">{error}</Typography>;
  if (!rules) return <Typography>Loading…</Typography>;

  return (
    <Stack spacing={2}>
      <Typography variant="h4" sx={{ fontWeight: 700 }}>
        Policy Manager
      </Typography>
      {rules.rules.map((rule, index) => (
        <Paper key={rule.id} sx={{ p: 2 }}>
          <Stack spacing={1}>
            <Typography variant="subtitle1">{rule.description}</Typography>
            <FormControlLabel
              control={
                <Switch checked={rule.enabled} onChange={(e) => updateRule(index, { enabled: e.target.checked })} />
              }
              label="Enabled"
            />
            <Stack direction="row" spacing={2} sx={{ alignItems: "center" }}>
              <Typography variant="body2">Threshold</Typography>
              <Slider
                value={rule.threshold}
                min={0}
                max={rule.condition === "max_harm_score" ? 7 : 1}
                step={rule.condition === "max_harm_score" ? 1 : 0.01}
                onChange={(_, value) => updateRule(index, { threshold: value as number })}
                sx={{ maxWidth: 300 }}
              />
              <TextField
                type="number"
                size="small"
                value={rule.threshold}
                onChange={(e) => updateRule(index, { threshold: Number(e.target.value) })}
                sx={{ width: 100 }}
              />
            </Stack>
            <TextField
              select
              label="Action"
              size="small"
              value={rule.action}
              onChange={(e) => updateRule(index, { action: e.target.value as PolicyRule["action"] })}
              sx={{ maxWidth: 200 }}
            >
              <MenuItem value="block">Block</MenuItem>
              <MenuItem value="flag">Flag</MenuItem>
              <MenuItem value="pass">Pass</MenuItem>
            </TextField>
            <FormControlLabel
              control={
                <Checkbox checked={rule.notify} onChange={(e) => updateRule(index, { notify: e.target.checked })} />
              }
              label="Notify"
            />
          </Stack>
        </Paper>
      ))}
      <Button variant="contained" onClick={handleSave} sx={{ alignSelf: "flex-start" }}>
        Save
      </Button>
      <Snackbar
        open={saved}
        autoHideDuration={4000}
        onClose={() => setSaved(false)}
        message="Rule changes will take effect within 60 seconds"
      />
      <Snackbar
        open={error !== null}
        autoHideDuration={6000}
        onClose={() => setError(null)}
        message={error}
      />
    </Stack>
  );
}
