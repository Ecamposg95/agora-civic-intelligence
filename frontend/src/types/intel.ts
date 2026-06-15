export interface IeemDataset {
  key: string;
  label: string;
  columns: string[];
  rows: Record<string, string>[];
  count: number;
  source: string;
  url: string;
}
export interface IeemDatasetRef {
  key: string;
  label: string;
}
export interface WbPoint {
  year: number;
  value: number;
}
export interface WbIndicator {
  indicator: string;
  label: string;
  points: WbPoint[];
  latest: WbPoint | null;
  source: string;
}
export interface WbIndicatorRef {
  code: string;
  label: string;
}
