import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Paper,
  Chip,
  Collapse,
  IconButton,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import type { WorkflowNodeConfig, WorkflowStepMeta, WorkflowTemplate } from '../../services/agents';
import { PROVIDER_OPTIONS } from '../../constants/agentWorkflow';

interface AgentWorkflowEditorProps {
  template: WorkflowTemplate | null;
  nodes: Record<string, WorkflowNodeConfig>;
  globalDefaults: {
    model_provider: string;
    model_name: string;
    temperature: number;
    max_tokens: number;
  };
  onChange: (nodes: Record<string, WorkflowNodeConfig>) => void;
}

const llmChipSx = { bgcolor: '#f0f5ff', color: '#667eea', fontWeight: 500, fontSize: 11 };
const sysChipSx = { bgcolor: '#f6ffed', color: '#52c41a', fontWeight: 500, fontSize: 11 };

function NodeModelFields({
  cfg,
  globalDefaults,
  onPatch,
}: {
  cfg: WorkflowNodeConfig;
  globalDefaults: AgentWorkflowEditorProps['globalDefaults'];
  onPatch: (patch: Partial<WorkflowNodeConfig>) => void;
}) {
  const inherit = !cfg.model_provider;
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 1 }}>
      <Typography variant="caption" sx={{ color: '#888' }}>
        模型配置（留空 Provider 则继承全局默认：{globalDefaults.model_provider} / {globalDefaults.model_name || '—'}）
      </Typography>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <FormControl size="small" sx={{ minWidth: 120, flex: 1 }}>
          <InputLabel>Provider</InputLabel>
          <Select
            label="Provider"
            value={cfg.model_provider ?? ''}
            onChange={(e) =>
              onPatch({ model_provider: e.target.value || null })
            }
          >
            <MenuItem value="">继承全局</MenuItem>
            {PROVIDER_OPTIONS.map((o) => (
              <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          size="small"
          label="模型名称"
          placeholder={inherit ? globalDefaults.model_name : ''}
          value={cfg.model_name ?? ''}
          onChange={(e) => onPatch({ model_name: e.target.value || null })}
          sx={{ flex: 1, minWidth: 120 }}
        />
      </Box>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          size="small"
          label="温度"
          type="number"
          inputProps={{ min: 0, max: 1, step: 0.1 }}
          placeholder={inherit ? String(globalDefaults.temperature) : ''}
          value={cfg.temperature ?? ''}
          onChange={(e) =>
            onPatch({
              temperature: e.target.value === '' ? null : Number(e.target.value),
            })
          }
          fullWidth
        />
        <TextField
          size="small"
          label="Max Tokens"
          type="number"
          placeholder={inherit ? String(globalDefaults.max_tokens) : ''}
          value={cfg.max_tokens ?? ''}
          onChange={(e) =>
            onPatch({
              max_tokens: e.target.value === '' ? null : Number(e.target.value),
            })
          }
          fullWidth
        />
      </Box>
    </Box>
  );
}

function LlmNodeEditor({
  cfg,
  fieldMeta,
  globalDefaults,
  onPatch,
}: {
  cfg: WorkflowNodeConfig;
  fieldMeta: WorkflowTemplate['node_fields'][string] | undefined;
  globalDefaults: AgentWorkflowEditorProps['globalDefaults'];
  onPatch: (patch: Partial<WorkflowNodeConfig>) => void;
}) {
  const fields = fieldMeta?.fields ?? ['system_prompt', 'model'];
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {fields.includes('system_prompt') && (
        <TextField
          label={fieldMeta?.system_prompt?.label ?? '系统提示词'}
          value={cfg.system_prompt ?? ''}
          onChange={(e) => onPatch({ system_prompt: e.target.value })}
          fullWidth
          multiline
          minRows={4}
          size="small"
          helperText={fieldMeta?.system_prompt?.hint}
        />
      )}
      {fields.includes('user_prompt_template') && (
        <TextField
          label={fieldMeta?.user_prompt_template?.label ?? '用户提示词模板'}
          value={cfg.user_prompt_template ?? ''}
          onChange={(e) => onPatch({ user_prompt_template: e.target.value })}
          fullWidth
          multiline
          minRows={4}
          size="small"
          helperText={fieldMeta?.user_prompt_template?.hint}
        />
      )}
      {fields.includes('model') && (
        <NodeModelFields
          cfg={cfg}
          globalDefaults={globalDefaults}
          onPatch={onPatch}
        />
      )}
    </Box>
  );
}

const AgentWorkflowEditor: React.FC<AgentWorkflowEditorProps> = ({
  template,
  nodes,
  globalDefaults,
  onChange,
}) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    intent: true,
    nl2sql: true,
  });

  const steps = template?.steps ?? [];
  const nodeFields = template?.node_fields ?? {};

  const patchNode = (nodeId: string, patch: Partial<WorkflowNodeConfig>) => {
    onChange({
      ...nodes,
      [nodeId]: { ...nodes[nodeId], ...patch },
    });
  };

  const toggle = (id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const renderStep = (step: WorkflowStepMeta, index: number) => {
    const isLlm = step.kind === 'llm';
    const isOtherBranch = step.path === 'other';
    const isAskBranch = step.path === 'ask_data';

    return (
      <Box key={step.id} sx={{ display: 'flex', gap: 1.5 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 28, flexShrink: 0 }}>
          <Box
            sx={{
              width: 24,
              height: 24,
              borderRadius: '50%',
              bgcolor: isLlm ? '#667eea' : '#e8e8e8',
              color: isLlm ? '#fff' : '#666',
              fontSize: 11,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {index + 1}
          </Box>
          {index < steps.length - 1 && (
            <Box sx={{ width: 2, flex: 1, minHeight: 12, bgcolor: '#e8e8e8', my: 0.5 }} />
          )}
        </Box>

        <Paper
          variant="outlined"
          sx={{
            flex: 1,
            mb: 1.5,
            borderColor: isOtherBranch ? '#ffe7ba' : isAskBranch ? '#d6e4ff' : '#e8e8e8',
            bgcolor: isOtherBranch ? '#fffbf0' : isAskBranch ? '#fafbff' : '#fff',
            overflow: 'hidden',
          }}
        >
          <Box
            sx={{
              px: 1.5,
              py: 1,
              display: 'flex',
              alignItems: 'flex-start',
              gap: 1,
              cursor: isLlm ? 'pointer' : 'default',
            }}
            onClick={() => isLlm && toggle(step.id)}
          >
            <Box sx={{ flex: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.25 }}>
                {isLlm ? (
                  <SmartToyOutlinedIcon sx={{ fontSize: 16, color: '#667eea' }} />
                ) : (
                  <SettingsOutlinedIcon sx={{ fontSize: 16, color: '#52c41a' }} />
                )}
                <Typography variant="body2" sx={{ fontWeight: 600, fontSize: 13 }}>
                  {step.title}
                </Typography>
                <Chip
                  size="small"
                  label={isLlm ? 'LLM 节点' : '系统节点'}
                  sx={isLlm ? llmChipSx : sysChipSx}
                />
                {step.path === 'other' && (
                  <Chip size="small" label="other 分支" sx={{ fontSize: 11 }} variant="outlined" />
                )}
                {step.path === 'ask_data' && (
                  <Chip size="small" label="ask_data 分支" sx={{ fontSize: 11 }} variant="outlined" />
                )}
              </Box>
              <Typography variant="caption" sx={{ color: '#888', display: 'block' }}>
                {step.description}
              </Typography>
            </Box>
            {isLlm && (
              <IconButton size="small" sx={{ mt: -0.5 }}>
                {expanded[step.id] ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            )}
          </Box>

          {isLlm && nodes[step.id] && (
            <Collapse in={expanded[step.id] !== false}>
              <Box sx={{ px: 1.5, pb: 1.5, pt: 0, borderTop: '1px solid #f0f0f0' }}>
                <LlmNodeEditor
                  cfg={nodes[step.id]}
                  fieldMeta={nodeFields[step.id]}
                  globalDefaults={globalDefaults}
                  onPatch={(patch) => patchNode(step.id, patch)}
                />
              </Box>
            </Collapse>
          )}
        </Paper>
      </Box>
    );
  };

  if (!template) {
    return (
      <Typography variant="body2" color="text.secondary">
        工作流模板加载中…
      </Typography>
    );
  }

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: 13, mb: 0.5 }}>
        固定工作流
      </Typography>
      <Typography variant="caption" sx={{ color: '#888', display: 'block', mb: 1.5 }}>
        流程顺序固定，不可调整节点顺序或停用。LLM 节点可编辑提示词与模型；系统节点为只读说明。
      </Typography>
      {steps.map((step: WorkflowStepMeta, index: number) => renderStep(step, index))}
    </Box>
  );
};

export default AgentWorkflowEditor;
