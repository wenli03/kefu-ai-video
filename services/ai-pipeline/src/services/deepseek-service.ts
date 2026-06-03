import axios from 'axios';

const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY || '';
const DEEPSEEK_BASE = 'https://api.deepseek.com';

export function getDeepseekService() {
  return {
    async ask(question: string, _context: string[]): Promise<string> {
      if (DEEPSEEK_API_KEY && DEEPSEEK_API_KEY.length > 10) {
        try {
          const { data } = await axios.post(
            `${DEEPSEEK_BASE}/v1/chat/completions`,
            {
              model: 'deepseek-chat',
              messages: [
                { role: 'system', content: '你是保险客服，根据已知信息直接回答用户问题。' },
                { role: 'user', content: `已知信息：${_context.join('\n\n')}\n\n用户问题：${question}\n\n请根据已知信息回答用户问题：` },
              ],
              temperature: 0.3,
              max_tokens: 500,
            },
            {
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${DEEPSEEK_API_KEY}` },
              timeout: 30000,
            }
          );
          const answer = data.choices[0]?.message?.content || '';
          if (answer && !answer.includes('请问') && answer.length > 20) return answer;
        } catch (e: any) {
          console.log(`[DeepSeek] API error: ${e.message}`);
        }
      }
      return fallbackAnswer(question);
    },
  };
}

function fallbackAnswer(question: string): string {
  console.log(`[DEEPSEEK] fallbackAnswer called with: "${question}"`);
  const q = question;
  if (q.includes('理赔') || q.includes('索赔')) return '理赔流程：1. 拨打95511报案 2. 准备身份证、保单、医疗记录等材料 3. 提交审核（3-5个工作日）4. 赔付到账。如有疑问可拨打95511咨询。';
  if (q.includes('退保') || q.includes('退款')) return '退保规则：投保后10天犹豫期内可全额退款。超过犹豫期退保按现金价值返还。需准备保单、身份证、银行卡办理。';
  if (q.includes('续保') || q.includes('续费')) return '续保政策：保障到期前30天可办理，无需重新核保，保费按原费率或调整后计算。';
  if (q.includes('投保') || q.includes('购买')) return '投保流程：1. 选择产品（寿险、健康险、意外险、车险）2. 填写信息 3. 健康告知 4. 支付保费 5. 生效（24小时在线办理）。';
  if (q.includes('保险') || q.includes('产品')) return '我们提供：寿险（保障生命）、健康险（保障医疗）、意外险（保障事故）、车险（保障车辆）。24小时在线投保，拨打95511咨询。';
  return '您好，您想了解什么？我可以帮您解答保险种类、投保流程、理赔流程、退保规则或续保政策等问题。';
}
