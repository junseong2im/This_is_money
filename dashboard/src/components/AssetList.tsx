import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { Position } from '../types';

interface AssetListProps {
  positions: Position[];
}

const AssetList: React.FC<AssetListProps> = ({ positions }) => {
  // [안전장치 1] positions가 배열이 아니거나 undefined면 렌더링 방지
  if (!positions || !Array.isArray(positions)) {
    return (
        <div className="p-8 text-center text-slate-600 italic text-xs">
            포지션 데이터를 불러오는 중...
        </div>
    );
  }

  return (
    <table className="w-full text-left border-collapse">
      <thead className="sticky top-0 z-10 bg-[#070B12]/60 backdrop-blur">
        <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-white/10">
          <th className="p-2 font-medium">자산</th>
          <th className="p-2 text-right font-medium">현재가</th>
          <th className="p-2 text-right font-medium">수량</th>
          <th className="p-2 text-right font-medium">손익</th>
        </tr>
      </thead>
      <tbody>
        {positions.map((pos, idx) => {
          // [안전장치 2] 필수 데이터가 없으면 스킵하거나 기본값 처리
          if (!pos) return null;
          const safeSymbol = pos.symbol || 'UNKNOWN';
          const safePrice = Number.isFinite(pos.currentPrice) ? pos.currentPrice : 0;
          const safeAmt = Number.isFinite(pos.amount) ? pos.amount : 0;
          const safePnlPct = Number.isFinite(pos.pnlPercentage) ? pos.pnlPercentage : 0;
          const safeNetPnl = Number.isFinite(pos.netPnL) ? pos.netPnL : 0;

          return (
            <tr key={safeSymbol + idx} className="border-b border-white/5 hover:bg-white/5 transition-colors text-xs group">
              <td className="p-2 font-semibold text-slate-100 group-hover:text-emerald-300 transition-colors">
                  {/* USDT 제거 전 symbol 존재 여부 확인 */}
                  {safeSymbol.replace('USDT', '')}
                  <span className="text-[9px] text-slate-500 font-normal ml-1">USDT</span>
              </td>
              <td className="p-2 text-right text-slate-200 font-mono">
                {safePrice.toLocaleString()}
                <span className="text-[9px] text-slate-500 font-normal ml-1">USDT</span>
              </td>
              <td className="p-2 text-right text-slate-200 font-mono">{Math.abs(safeAmt).toFixed(3)}</td>
              <td className={`p-2 text-right flex justify-end items-center gap-1 ${safePnlPct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {safePnlPct >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                <span className="font-mono">{safePnlPct.toFixed(2)}%</span>
                <span className="text-[10px] opacity-70 font-mono">({safeNetPnl >= 0 ? '+' : ''}{safeNetPnl.toFixed(2)} USDT)</span>
              </td>
            </tr>
          );
        })}
        {positions.length === 0 && (
          <tr>
            <td colSpan={4} className="p-8 text-center text-slate-600 italic text-xs">
              보유 중인 포지션이 없습니다. <br/> 신호를 탐색 중...
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
};

export default AssetList;