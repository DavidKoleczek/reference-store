import { readAppNetwork, type AppNetwork } from "@/lib/api";

// Without the server's word, the page is taken to be on another device, which shows less rather than more.
let network: AppNetwork = { this_machine: false, lan_url: null, qr_code: null };

/** Reads where the page is, before the app is first drawn. */
export async function loadNetwork() {
  try {
    network = await readAppNetwork();
  } catch {
    // Kept as another device's.
  }
}

/** Where the page is, as the server said when the app started. */
export function appNetwork(): AppNetwork {
  return network;
}
