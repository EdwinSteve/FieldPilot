import { useEffect, useState } from "react";
import { session } from "../api/session";

/**
 * An image from the farm's API as a local URL. Every farm route needs the token
 * (D082), and an <img> cannot send one, so the image is fetched and handed over.
 */
export function useFarmImage(url: string): string | null {
  const [loaded, setLoaded] = useState<{ url: string; src: string } | null>(null);

  useEffect(() => {
    let live = true;
    let src: string | null = null;
    session
      .blob(url)
      .then((blob) => {
        if (!live) return;
        src = URL.createObjectURL(blob);
        setLoaded({ url, src });
      })
      .catch(() => undefined);
    return () => {
      live = false;
      if (src !== null) URL.revokeObjectURL(src);
    };
  }, [url]);

  return loaded?.url === url ? loaded.src : null;
}
