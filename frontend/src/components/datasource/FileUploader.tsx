import React, { useCallback, useState, useRef } from 'react';
import { Box, Typography, LinearProgress } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

interface FileUploaderProps {
  onUpload: (file: File) => Promise<void>;
  accept?: string;
}

const FileUploader: React.FC<FileUploaderProps> = ({ onUpload, accept = '.xlsx,.xls,.csv' }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file) return;
      setUploading(true);
      setProgress(0);

      const interval = setInterval(() => {
        setProgress((p) => Math.min(p + 10, 90));
      }, 200);

      try {
        await onUpload(file);
        setProgress(100);
      } catch {
        setProgress(0);
      } finally {
        clearInterval(interval);
        setTimeout(() => setUploading(false), 500);
      }
    },
    [onUpload]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      handleFile(file);
    },
    [handleFile]
  );

  const handleClick = () => inputRef.current?.click();
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <Box
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={handleClick}
      sx={{
        border: 2,
        borderStyle: 'dashed',
        borderColor: isDragging ? 'primary.main' : 'divider',
        borderRadius: 2,
        p: 4,
        textAlign: 'center',
        cursor: 'pointer',
        transition: 'all 0.2s',
        bgcolor: isDragging ? 'action.hover' : 'transparent',
        '&:hover': { borderColor: 'primary.light' },
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        hidden
        onChange={handleInputChange}
      />
      {uploading ? (
        <Box>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            正在上传...
          </Typography>
          <LinearProgress variant="determinate" value={progress} />
        </Box>
      ) : (
        <>
          <CloudUploadIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
          <Typography variant="body1" gutterBottom>
            拖拽文件到此处，或点击选择文件
          </Typography>
          <Typography variant="caption" color="text.secondary">
            支持 {accept} 格式
          </Typography>
        </>
      )}
    </Box>
  );
};

export default FileUploader;
