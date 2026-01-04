export enum StartParamKey {
  INVITE = 'i',
  REFERAL = 'r', // Note: Keep typo for backend compatibility
  MODE = 'm',
  PAGE = 'p',
}

export interface StartParamData {
  type: StartParamKey | null;
  value: string | null;
  rawParam: string | null;
}
