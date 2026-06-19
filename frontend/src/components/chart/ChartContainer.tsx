import React, { useMemo, useState } from 'react';
import { Box, ToggleButton, ToggleButtonGroup } from '@mui/material';
import ReactEChartsCore from 'echarts-for-react';
import type { TableData } from '../../types/api';
import type { ChartView } from '../../utils/chartConvert';
import {
  CHART_TYPE_LABELS,
  chartViewToChartData,
  getVisualChartTypes,
  isVisualChartType,
} from '../../utils/chartConvert';
import DataTable from './DataTable';

interface ChartContainerProps {
  chartView: ChartView;
  chartType?: string;
  tableData?: TableData;
  height?: number;
}

const BAR_MAX_WIDTH = 32;

const ChartContainer: React.FC<ChartContainerProps> = ({
  chartView,
  chartType,
  tableData,
  height = 350,
}) => {
  const visualTypes = useMemo(
    () => getVisualChartTypes(chartView.availableTypes),
    [chartView.availableTypes],
  );

  const switcherTypes = chartView.availableTypes.filter(
    (t) => t === 'table' || visualTypes.includes(t),
  );

  const [selectedType, setSelectedType] = useState(() => {
    if (chartType && switcherTypes.includes(chartType)) return chartType;
    if (visualTypes.includes(chartView.defaultType)) return chartView.defaultType;
    return visualTypes[0] || chartView.defaultType || 'table';
  });

  const handleTypeChange = (_: React.MouseEvent<HTMLElement>, value: string | null) => {
    if (!value) return;
    setSelectedType(value);
  };

  const data = useMemo(
    () => (isVisualChartType(selectedType) ? chartViewToChartData(chartView, selectedType) : null),
    [chartView, selectedType],
  );

  const option = useMemo(() => {
    if (!data?.series?.length) {
      return {
        xAxis: { type: 'category', data: [] },
        yAxis: { type: 'value' },
        series: [],
      };
    }

    const isCombo = selectedType === 'bar_line' || new Set(data.series.map((s) => s.type)).size > 1;
    const useDualAxis = isCombo && data.series.some((s) => (s.yAxisIndex ?? 0) === 1);

    return {
      tooltip: { trigger: 'axis' as const },
      legend: { bottom: 0 },
      grid: { left: 60, right: useDualAxis ? 60 : 20, top: 48, bottom: 48 },
      xAxis: {
        type: 'category' as const,
        data: data.x_axis || [],
        axisLabel: { rotate: data.x_axis && data.x_axis.length > 8 ? 45 : 0 },
      },
      yAxis: useDualAxis
        ? [
            { type: 'value' as const, name: data.series[0]?.name || '' },
            { type: 'value' as const, name: data.series[1]?.name || '', splitLine: { show: false } },
          ]
        : { type: 'value' as const },
      series: data.series.map((s) => ({
        name: s.name,
        type: s.type === 'line' ? 'line' : 'bar',
        data: s.data,
        yAxisIndex: s.yAxisIndex ?? 0,
        smooth: s.type === 'line',
        ...(s.type === 'line'
          ? { symbol: 'circle', symbolSize: 6 }
          : { barMaxWidth: BAR_MAX_WIDTH }),
      })),
    };
  }, [data, selectedType]);

  if (switcherTypes.length === 0) {
    return null;
  }

  const showTable = selectedType === 'table' && tableData;
  const showChart = isVisualChartType(selectedType) && data;

  return (
    <Box sx={{ position: 'relative', mt: 1.5, minHeight: showChart ? height : undefined }}>
      {switcherTypes.length > 1 && (
        <Box sx={{ position: 'absolute', top: 4, left: 4, zIndex: 1 }}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={selectedType}
            onChange={handleTypeChange}
            sx={{
              bgcolor: 'background.paper',
              boxShadow: 1,
              '& .MuiToggleButton-root': {
                px: 1,
                py: 0.25,
                fontSize: 12,
                lineHeight: 1.4,
                textTransform: 'none',
              },
            }}
          >
            {switcherTypes.map((t) => (
              <ToggleButton key={t} value={t}>
                {CHART_TYPE_LABELS[t] || t}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>
      )}
      {showChart && <ReactEChartsCore option={option} style={{ height }} notMerge />}
      {showTable && (
        <Box sx={{ pt: switcherTypes.length > 1 ? 5 : 0 }}>
          <DataTable data={tableData} />
        </Box>
      )}
    </Box>
  );
};

export default ChartContainer;
