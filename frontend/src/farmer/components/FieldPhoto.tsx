import { boxRect } from "../../lib/imagery";
import type { NormBox } from "../../types/api";
import { en } from "../i18n/en";
import { useFarmImage } from "../hooks/useFarmImage";
import { bareSpotRings } from "../lib/bareSpotRings";

const WIDTH = 512;
const HEIGHT = 256;

interface FieldPhotoProps {
  imageUrl: string;
  alt: string;
  zoneLabel: string;
  zoneArea: NormBox;
  spots: NormBox[];
}

/** The satellite photo, with the zone outlined and a ring on each bare spot. */
export function FieldPhoto({ imageUrl, alt, zoneLabel, zoneArea, spots }: FieldPhotoProps) {
  const zone = boxRect(zoneArea);
  const src = useFarmImage(imageUrl);
  return (
    <figure className="flex flex-col gap-2.5 rounded-card bg-surface p-2.5">
      <div className="relative aspect-[2/1] w-full overflow-hidden rounded-tile bg-field">
        {src === null ? null : <img src={src} alt={alt} className="absolute inset-0 size-full" />}
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="none"
          aria-hidden="true"
          className="absolute inset-0 size-full"
        >
          <rect
            x={zone.x * WIDTH + 2}
            y={zone.y * HEIGHT + 2}
            width={zone.width * WIDTH - 4}
            height={zone.height * HEIGHT - 4}
            fill="none"
            stroke="var(--color-surface)"
            strokeWidth="3"
            strokeDasharray="10 6"
          />
          {bareSpotRings(spots, WIDTH, HEIGHT).map((ring) => (
            <circle
              key={`${ring.cx},${ring.cy}`}
              cx={ring.cx}
              cy={ring.cy}
              r={ring.r}
              fill="none"
              stroke="var(--color-ring)"
              strokeWidth="5"
            />
          ))}
        </svg>
        <span className="absolute top-2.5 right-2.5 rounded-pill bg-surface px-2.5 py-1 text-caption font-extrabold text-ink">
          {zoneLabel}
        </span>
      </div>
      <figcaption className="flex items-center gap-2 px-1 text-caption text-ink-2">
        <span className="size-4.5 shrink-0 rounded-full border-3 border-ring" />
        {en.field.spotsLegend}
      </figcaption>
    </figure>
  );
}
