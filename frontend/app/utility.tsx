import type { ImagePickerAsset } from 'expo-image-picker';
import { Platform } from 'react-native';

const API_BASE = process.env.EXPO_PUBLIC_API_BASE || 'http://192.168.2.38:8000';

function extToMime(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  switch (ext) {
    case 'jpg':
    case 'jpeg':
      return 'image/jpeg';
    case 'png':
      return 'image/png';
    case 'gif':
      return 'image/gif';
    case 'webp':
      return 'image/webp';
    case 'svg':
      return 'image/svg+xml';
    default:
      return 'application/octet-stream';
  }
}

/**
 * Fetch weekly ad JSON from the FastAPI endpoint.
 * @param storename - store identifier (query param `storename`)
 * @param week - week date string in YYYY-MM-DD (query param `week`)
 */
export async function get_store_ads(storename: string, week: string): Promise<any> {
  console.log('Fetching ads for store:', storename, 'week:', week);
  console.log('Fetching ads for store2:', storename, 'week:', week);
  if (!storename) throw new Error('storename is required');
  if (!week) throw new Error('week is required');
  const url = `${API_BASE}/weeklyadfromfile/?storename=${encodeURIComponent(storename)}&week=${encodeURIComponent(week)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Failed to fetch store ads: ${res.status} ${body}`);
  }
  console.log('response json', { status: res.status, url });
  const bodyPreview = await res.clone().text().then((t) => t.slice(0, 500)).catch(() => '');
  console.log('response body preview', bodyPreview);
  return res.json();
}

/**
 * Fetch image bytes (base64) from the FastAPI endpoint and return a data URI.
 * @param storename - store identifier
 * @param week - week date string in YYYY-MM-DD
 * @param imageFilename - filename of the image
 */
export async function get_image(storename: string, week: string, imageFilename: string): Promise<string> {
  if (!storename) throw new Error('storename is required');
  if (!week) throw new Error('week is required');
  if (!imageFilename) throw new Error('imageFilename is required');

  const url = `${API_BASE}/getimagebytes/?storename=${encodeURIComponent(storename)}&week=${encodeURIComponent(week)}&image_filename=${encodeURIComponent(imageFilename)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Failed to fetch image bytes: ${res.status} ${body}`);
  }
  const json = await res.json();
  const b64 = json?.image_bytes;
  if (!b64) throw new Error('No image_bytes returned from server');
  const mime = extToMime(imageFilename);
  return `data:${mime};base64,${b64}`;
}

async function buildUploadFormData(asset: ImagePickerAsset): Promise<FormData> {
  if (!asset?.uri) {
    throw new Error('Image asset is missing a URI');
  }

  const form = new FormData();
  const fileName = asset.fileName ?? `fridge-${Date.now()}.jpg`;
  const mimeType = asset.mimeType ?? extToMime(fileName);

  if (Platform.OS === 'web') {
    const response = await fetch(asset.uri);
    const blob = await response.blob();
    const type = mimeType || blob.type || 'application/octet-stream';
    const file = new File([blob], fileName, { type });
    form.append('file', file);
  } else {
    form.append('file', {
      uri: asset.uri,
      name: fileName,
      type: mimeType,
    } as any);
  }

  return form;
}

type HttpError = Error & { status?: number };

async function postImageForAnalysis(asset: ImagePickerAsset, endpoint: string) {
  const formData = await buildUploadFormData(asset);
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
    },
    body: formData,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    const err = new Error(`Image analysis failed: ${res.status} ${body}`) as HttpError;
    err.status = res.status;
    throw err;
  }

  return res.json();
}

export async function analyze_photo(asset: ImagePickerAsset, endpoint: string = '/analyze-fridge/'): Promise<any> {
  const candidates = [endpoint, '/analyze-fridge', '/analyze_photo', '/analyze_fridge'];
  const tried = new Set<string>();
  let lastError: Error | null = null;

  for (const path of candidates) {
    if (tried.has(path)) continue;
    tried.add(path);

    try {
      return await postImageForAnalysis(asset, path);
    } catch (err: any) {
      if (err?.status !== 404) {
        throw err;
      }
      lastError = err;
    }
  }

  throw lastError ?? new Error('Image analysis failed: endpoint not found');
}

export default {
  get_store_ads,
  get_image,
  analyze_photo,
};
