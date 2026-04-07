import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface ExpandableImageProps {
  src: string;
  alt: string;
  className?: string;
  imageClassName?: string;
}

export default function ExpandableImage({
  src,
  alt,
  className,
  imageClassName,
}: ExpandableImageProps) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          className={className}
          type="button"
        >
          <img
            alt={alt}
            className={imageClassName}
            src={src}
          />
        </button>
      </DialogTrigger>
      <DialogContent className="max-h-[92vh] max-w-6xl border-border bg-card p-3 sm:p-4">
        <DialogTitle className="sr-only">{alt}</DialogTitle>
        <div className="overflow-hidden rounded-2xl border border-border bg-background/60">
          <img
            alt={alt}
            className="max-h-[82vh] w-full object-contain"
            src={src}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
