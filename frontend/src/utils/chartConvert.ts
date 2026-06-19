import type { ChartData, ChartSeries } from '../types/api';

export type ChartOptionSeries = {
  name?: string;
  type?: string;
  data?: number[];
  yAxisIndex?: number;
};

export type ChartPayload = {
  default_type?: string;
  available_types?: string[];
  type?: string;
  x_axis?: string[];
  options?: Record<string, { series?: ChartOptionSeries[] }>;
  series?: ChartOptionSeries[];
  data?: Array<{ name?: string; value?: number }>;
  config?: { y_label?: string; x_label?: string; title?: string };
};

export type ChartView = {
  defaultType: string;
  availableTypes: string[];
  xAxis: string[];
  options: Record<string, { series: ChartSeries[] }>;
  config?: ChartPayload['config'];
};

export const CHART_TYPE_LABELS: Record<string, string> = {
  bar: '柱状图',
  line: '折线图',
  bar_line: '柱线复合',
  table: '表格',
};

export function isVisualChartType(type?: string | null): boolean {
  return type === 'bar' || type === 'line' || type === 'bar_line';
}

export function getVisualChartTypes(types: string[] = []): string[] {
  return types.filter((t) => isVisualChartType(t));
}

function normalizeSeries(series: ChartOptionSeries[] = []): ChartSeries[] {
  return series.map((s) => ({
    name: s.name || '值',
    type: (s.type === 'line' ? 'line' : 'bar') as ChartSeries['type'],
    data: s.data || [],
    yAxisIndex: s.yAxisIndex ?? 0,
  }));
}

export function resolveChartView(parsed: ChartPayload | undefined): ChartView | null {
  if (!parsed) return null;

  const availableTypes = parsed.available_types?.length
    ? parsed.available_types
    : parsed.type
      ? [parsed.type]
      : [];

  const defaultType = parsed.default_type || parsed.type || availableTypes[0] || 'table';
  const xAxis = parsed.x_axis || [];

  const options: Record<string, { series: ChartSeries[] }> = {};
  if (parsed.options && Object.keys(parsed.options).length > 0) {
    for (const [key, val] of Object.entries(parsed.options)) {
      if (val?.series?.length) {
        options[key] = { series: normalizeSeries(val.series) };
      }
    }
  } else if (parsed.series?.length && isVisualChartType(defaultType)) {
    options[defaultType] = { series: normalizeSeries(parsed.series) };
  } else if (parsed.data?.length && isVisualChartType(defaultType)) {
    const names = parsed.data.map((p) => String(p.name ?? ''));
    const values = parsed.data.map((p) => Number(p.value ?? 0));
    const seriesType = defaultType === 'line' ? 'line' : 'bar';
    options[defaultType] = {
      series: [{
        name: parsed.config?.y_label || '值',
        type: seriesType,
        data: values,
        yAxisIndex: 0,
      }],
    };
    if (!xAxis.length) {
      return {
        defaultType,
        availableTypes,
        xAxis: names,
        options,
        config: parsed.config,
      };
    }
  }

  if (Object.keys(options).length === 0) return null;

  return {
    defaultType,
    availableTypes,
    xAxis,
    options,
    config: parsed.config,
  };
}

export function chartViewToChartData(view: ChartView, chartType: string): ChartData | null {
  const option = view.options[chartType];
  if (!option?.series?.length) return null;
  return { x_axis: view.xAxis, series: option.series };
}

export function apiChartToChartData(parsed: ChartPayload): ChartData | null {
  const view = resolveChartView(parsed);
  if (!view) return null;
  const type = isVisualChartType(parsed.default_type || parsed.type)
    ? (parsed.default_type || parsed.type)!
    : getVisualChartTypes(view.availableTypes)[0];
  if (!type) return null;
  return chartViewToChartData(view, type);
}

export function chartPayloadToChartData(
  chartPayload: ChartPayload | undefined,
): { chartView?: ChartView; chartData?: ChartData; chartType?: string } {
  const view = resolveChartView(chartPayload);
  if (!view) return {};
  const defaultType = view.defaultType;
  if (!isVisualChartType(defaultType)) {
    return { chartView: view, chartType: defaultType };
  }
  const chartData = chartViewToChartData(view, defaultType);
  if (!chartData) return { chartView: view, chartType: defaultType };
  return { chartView: view, chartData, chartType: defaultType };
}
