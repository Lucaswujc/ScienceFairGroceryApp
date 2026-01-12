export type Ad = {
  product: string;
  price: string | number;
  image_base64?: string | null;
  image_uri?: string | null;
  image_filename?: string | null;
  store?: string;
  date?: string;
};
