import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Select,
  MenuItem,
  Checkbox,
  Button,
  Typography,
  Paper,
} from '@mui/material';

export interface EditableField {
  id: number;
  column_name: string;
  column_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  description: string;
}

interface FieldEditDialogProps {
  open: boolean;
  onClose: () => void;
  tableName: string;
  fields: EditableField[];
  onSave: (fields: EditableField[]) => void;
}

const typeOptions = ['INTEGER', 'TEXT', 'REAL', 'BLOB', 'NUMERIC'];

const FieldEditDialog: React.FC<FieldEditDialogProps> = ({
  open,
  onClose,
  tableName,
  fields,
  onSave,
}) => {
  const [localFields, setLocalFields] = useState<EditableField[]>(fields);

  React.useEffect(() => {
    setLocalFields(fields);
  }, [fields]);

  const updateField = (id: number, key: keyof EditableField, value: string | boolean) => {
    setLocalFields((prev) =>
      prev.map((f) => (f.id === id ? { ...f, [key]: value } : f))
    );
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ fontWeight: 600 }}>
        ✏️ 编辑字段 — {tableName}
      </DialogTitle>
      <DialogContent sx={{ maxHeight: '65vh', overflow: 'auto' }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          修改字段的名称、类型、描述等信息，修改后的 Schema 将影响 NL2SQL 的准确性
        </Typography>
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" sx={{ '& th, & td': { fontSize: 13 } }}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 500 }}>字段名</TableCell>
                <TableCell sx={{ fontWeight: 500 }}>类型</TableCell>
                <TableCell sx={{ fontWeight: 500 }}>可空</TableCell>
                <TableCell sx={{ fontWeight: 500 }}>主键</TableCell>
                <TableCell sx={{ fontWeight: 500 }}>业务描述</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {localFields.map((field) => (
                <TableRow key={field.id}>
                  <TableCell>
                    <TextField
                      size="small"
                      value={field.column_name}
                      onChange={(e) => updateField(field.id, 'column_name', e.target.value)}
                      sx={{ width: 90, '& input': { fontSize: 12, py: 0.5 } }}
                    />
                  </TableCell>
                  <TableCell>
                    <Select
                      size="small"
                      value={field.column_type}
                      onChange={(e) => updateField(field.id, 'column_type', e.target.value)}
                      sx={{ fontSize: 12, '& .MuiSelect-select': { py: 0.5 } }}
                    >
                      {typeOptions.map((t) => (
                        <MenuItem key={t} value={t} sx={{ fontSize: 12 }}>
                          {t}
                        </MenuItem>
                      ))}
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Checkbox
                      size="small"
                      checked={field.is_nullable}
                      onChange={(e) => updateField(field.id, 'is_nullable', e.target.checked)}
                      sx={{ '& .MuiSvgIcon-root': { fontSize: 18 } }}
                    />
                  </TableCell>
                  <TableCell>
                    <Checkbox
                      size="small"
                      checked={field.is_primary_key}
                      onChange={(e) => updateField(field.id, 'is_primary_key', e.target.checked)}
                      sx={{ '& .MuiSvgIcon-root': { fontSize: 18 } }}
                    />
                  </TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      value={field.description}
                      onChange={(e) => updateField(field.id, 'description', e.target.value)}
                      sx={{ width: 130, '& input': { fontSize: 12, py: 0.5 } }}
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 1.5 }}>
        <Button onClick={onClose} color="inherit">
          取消
        </Button>
        <Button
          variant="contained"
          onClick={() => {
            onSave(localFields);
            onClose();
          }}
          sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#7c93f5' } }}
        >
          保存
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default FieldEditDialog;
