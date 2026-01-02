const API_BASE = process.env.EXPO_PUBLIC_API_BASE || 'http://localhost:8000';



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

export default {
  get_store_ads,
  get_image,
};
