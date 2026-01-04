export type PaymentCurrency = 'TELEGRAM_STARS' | 'YOOKASSA';

export interface Product {
  id: string;
  name: string;
  price: number;
  currency: string;
  duration_days: number;
  is_recurring: boolean;
}

export interface StartPurchaseRequest {
  product_id: string;
  currency: string;
  provider_id: string;
  return_url: string;
}

export interface StartPurchaseResponse {
  payment_id: string;
  confirmation_url: string;
  amount: number;
  currency: string;
}

export interface CreateInvoiceRequest {
  product_id: string;
}

export interface CreateInvoiceResponse {
  invoice_url: string;
  invoice_id: string;
}
