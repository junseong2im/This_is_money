
import React from 'react';
import { Asset } from '../dashboard/types';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface AssetListProps {
  assets: Asset[];
}

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const AssetList: React.FC<AssetListProps> = ({ assets }) => {
  const data = assets.filter(a => a.held * a.price > 10).map(a => ({
    name: a.symbol,
    value: a.held * a.price
  }));

  return (
    <div className="flex flex-col h-full bg-slate-900/50 border border-slate-800 rounded-lg overflow-hidden">
      <div className="p-3 border-b border-slate-800 bg-slate-900">
        <h3 className="font-bold text-sm text-slate-300 uppercase tracking-wider">Portfolio Allocation</h3>
      </div>
      
      <div className="flex-1 p-4 flex flex-col md:flex-row gap-4">
        {/* Donut Chart */}
        <div className="h-40 w-full md:w-1/3 min-w-[120px]">
            <ResponsiveContainer width="100%" height="100%">
            <PieChart>
                <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={25}
                outerRadius={40}
                paddingAngle={5}
                dataKey="value"
                stroke="none"
                >
                {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
                </Pie>
                <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '4px' }}
                    itemStyle={{ color: '#fff' }}
                    formatter={(value: number) => `$${value.toFixed(0)}`}
                />
            </PieChart>
            </ResponsiveContainer>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto font-mono text-sm space-y-1">
          {assets.map((asset) => {
            const value = asset.held * asset.price;
            const isPositive = asset.change >= 0;
            return (
              <div key={asset.symbol} className="flex justify-between items-center p-2 hover:bg-slate-800/50 rounded transition-colors">
                <div>
                  <div className="font-bold text-slate-200">{asset.symbol}</div>
                  <div className="text-xs text-slate-500">{asset.name}</div>
                </div>
                <div className="text-right">
                  <div className="text-slate-200">${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                  <div className={`text-xs ${isPositive ? 'text-emerald-400' : 'text-rose-500'}`}>
                    {isPositive ? '+' : ''}{asset.change.toFixed(2)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AssetList;
