import path from 'path';

const VIDEO_DIR = path.join(__dirname, '..', '..', '..', '..', '..', 'assets', 'avatar-videos');

const VIDEO_MAP: Record<string, string[]> = {
  greeting: ['greeting.webm'],
  insurance: ['insurance-intro.webm'],
  claim: ['claim-guide.webm'],
  refund: ['refund-info.webm'],
  renewal: ['renewal-info.webm'],
  default: ['greeting.webm'],
};

export function getAvatarService() {
  return {
    matchVideo(answerText: string, question?: string): string | null {
      const getCategory = (txt: string): string | null => {
        const q = txt.toLowerCase();
        if (q.includes('退保') || q.includes('退款')) return 'refund';
        if (q.includes('续保') || q.includes('续费')) return 'renewal';
        if (q.includes('理赔') || q.includes('索赔')) return 'claim';
        if (q.includes('投保') || q.includes('购买') || q.includes('保险')) return 'insurance';
        return null;
      };

      // Match question first (most specific)
      let cat = getCategory(question || '');
      if (!cat) cat = getCategory(answerText);
      if (!cat) cat = 'greeting';

      const videos = VIDEO_MAP[cat] || VIDEO_MAP.default;
      return `/avatar-videos/${videos[0]}`;
    },

    getVideoUrl(videoPath: string): string {
      return videoPath;
    },
  };
}
