export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role_id: number | null;
  role_name: string;
  role_code?: string | null;
  is_active: boolean;
  created_at?: string;
}

export interface Role {
  id: number;
  name: string;
  code: string;
  description?: string;
  is_active: boolean;
  menus: Menu[];
  created_at: string;
  updated_at: string;
}

export interface Menu {
  id: number;
  name: string;
  icon?: string;
  path: string;
  parent_id?: number;
  sort_order: number;
  permission_code?: string;
  children?: Menu[];
  created_at: string;
  updated_at: string;
}

export interface DataSource {
  id: number;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DataSourceTable {
  id: number;
  datasource_id: number;
  table_name: string;
  table_comment?: string;
  columns: DataSourceColumn[];
  created_at: string;
}

export interface DataSourceColumn {
  id: number;
  table_id: number;
  column_name: string;
  column_type: string;
  column_comment?: string;
  is_primary_key: boolean;
}

export interface ExcelFile {
  id: number;
  filename: string;
  original_name: string;
  sheet_name: string;
  file_size: number;
  row_count: number;
  columns: ExcelColumn[];
  created_at: string;
}

export interface ExcelColumn {
  id: number;
  file_id: number;
  column_name: string;
  column_type: string;
}

export interface Conversation {
  id: number;
  title: string;
  model?: string;
  data_source_type?: 'db' | 'excel' | 'csv' | 'chat';
  db_connection_id?: number | null;
  file_upload_id?: number | null;
  agent_config_id?: number | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
  chart_data?: ChartData;
  chart_view?: ChartView;
  table_data?: TableData;
  chart_type?: string;
  metadata_json?: {
    sql?: string;
    table_data?: TableData;
    chart_data?: unknown;
    chart_type?: string;
  } | null;
  created_at: string;
}

export interface ChartData {
  x_axis?: string[];
  series: ChartSeries[];
}

export interface ChartView {
  defaultType: string;
  availableTypes: string[];
  xAxis: string[];
  options: Record<string, { series: ChartSeries[] }>;
  config?: { y_label?: string; x_label?: string; title?: string };
}

export interface ChartSeries {
  name: string;
  type: 'bar' | 'line';
  data: number[];
  yAxisIndex?: number;
}

export interface TableData {
  columns: string[];
  rows: Record<string, unknown>[];
}

export interface StreamEvent {
  event: 'token' | 'sql' | 'chart' | 'table' | 'error' | 'done';
  data: string;
}
