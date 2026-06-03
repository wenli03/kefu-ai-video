import path from 'path';
import fs from 'fs';

interface KnowledgeItem {
  id: string;
  title: string;
  content: string;
  category: string;
  keywords: string[];
}

const knowledgeBase: KnowledgeItem[] = [];

export function getRagService() {
  return {
    init(knowledgeDir: string): void {
      const filePath = path.join(knowledgeDir, 'insurance-qa.json');
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const items = JSON.parse(raw) as KnowledgeItem[];
        knowledgeBase.push(...items);
        console.log(`[RAG] Loaded ${knowledgeBase.length} knowledge items`);
      } else {
        console.log('[RAG] No knowledge file found, using built-in defaults');
        knowledgeBase.push(
          {
            id: '1', title: '理赔流程',
            content: '理赔流程：1.出险报案 2.准备材料 3.审核 4.赔付到账。报案电话：95511。材料包括身份证、保单、医疗记录。审核周期3-5个工作日。',
            category: '理赔', keywords: ['理赔', '索赔', '报案', '赔付'],
          },
          {
            id: '2', title: '投保指南',
            content: '投保流程：1.选择产品 2.填写信息 3.健康告知 4.支付保费 5.生效。产品包括寿险、健康险、意外险、车险。在线投保24小时可办理。',
            category: '投保', keywords: ['投保', '购买', '保险', '产品', '保费'],
          },
          {
            id: '3', title: '退保规则',
            content: '退保规则：犹豫期内（10天）全额退款。犹豫期后退保按现金价值返还。退保所需材料：保单、身份证、银行卡。',
            category: '退保', keywords: ['退保', '退款', '取消', '犹豫期'],
          },
          {
            id: '4', title: '续保政策',
            content: '续保政策：保障到期前30天可办理续保。续保无需重新核保。续保保费按原费率或调整后费率计算。',
            category: '续保', keywords: ['续保', '续费', '到期'],
          },
          {
            id: '5', title: '健康告知',
            content: '健康告知：投保时需如实填写健康状况。隐瞒病情可能导致理赔被拒。常见告知项包括既往病史、住院史、家族病史。',
            category: '投保', keywords: ['健康', '告知', '病史', '体检'],
          },
        );
      }
    },

    async search(query: string): Promise<string[]> {
      const results = knowledgeBase
        .map((item) => {
          const qLower = query.toLowerCase();
          const matchCount = item.keywords.filter((kw) =>
            qLower.includes(kw.toLowerCase())
          ).length;
          return { item, matchCount };
        })
        .filter((r) => r.matchCount > 0)
        .sort((a, b) => b.matchCount - a.matchCount)
        .slice(0, 5);

      if (results.length === 0) {
        return knowledgeBase.slice(0, 2).map((item) => item.content);
      }
      return results.map((r) => r.item.content);
    },

    async searchVector(query: string): Promise<string[]> {
      return this.search(query);
    },
  };
}
