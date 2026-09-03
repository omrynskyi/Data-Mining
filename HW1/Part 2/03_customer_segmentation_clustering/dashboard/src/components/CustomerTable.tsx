import { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, Search } from 'lucide-react';
import type { ClusterProfile, Customer } from '../types';
import { formatNumber } from '../lib/format';

interface CustomerTableProps {
  customers: Customer[];
  clusters: ClusterProfile[];
}

type SortKey = 'customer_id' | 'age' | 'annual_income' | 'spending_score' | 'cluster_id';

const COLUMNS: Array<{ key: SortKey | 'gender' | 'cluster_name'; label: string; sortable: boolean }> = [
  { key: 'customer_id', label: 'ID', sortable: true },
  { key: 'gender', label: 'Gender', sortable: false },
  { key: 'age', label: 'Age', sortable: true },
  { key: 'annual_income', label: 'Income (k$)', sortable: true },
  { key: 'spending_score', label: 'Spending', sortable: true },
  { key: 'cluster_id', label: 'Cluster', sortable: true },
  { key: 'cluster_name', label: 'Segment', sortable: false },
];

const PAGE_SIZE = 25;

export default function CustomerTable({ customers, clusters }: CustomerTableProps) {
  const [query, setQuery] = useState('');
  const [clusterFilter, setClusterFilter] = useState<number | 'all'>('all');
  const [sortKey, setSortKey] = useState<SortKey>('customer_id');
  const [ascending, setAscending] = useState(true);
  const [page, setPage] = useState(0);

  const colorFor = useMemo(() => {
    const map = new Map<number, string>();
    clusters.forEach((cluster) => map.set(cluster.cluster_id, cluster.color));
    return map;
  }, [clusters]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return customers
      .filter((customer) => clusterFilter === 'all' || customer.cluster_id === clusterFilter)
      .filter((customer) => {
        if (!needle) return true;
        return (
          String(customer.customer_id).includes(needle) ||
          customer.gender.toLowerCase().includes(needle) ||
          customer.cluster_name.toLowerCase().includes(needle)
        );
      })
      .sort((a, b) => {
        const delta = a[sortKey] - b[sortKey];
        return ascending ? delta : -delta;
      });
  }, [ascending, clusterFilter, customers, query, sortKey]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const rows = filtered.slice(currentPage * PAGE_SIZE, currentPage * PAGE_SIZE + PAGE_SIZE);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setAscending((value) => !value);
    } else {
      setSortKey(key);
      setAscending(true);
    }
    setPage(0);
  };

  return (
    <section className="panel" aria-label="Customer explorer">
      <header className="panel-header flex-col items-stretch gap-4 sm:flex-row sm:items-center">
        <div>
          <h2 className="panel-title">Customer explorer</h2>
          <p className="panel-subtitle">
            {filtered.length} of {customers.length} records
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="relative">
            <Search
              className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500"
              aria-hidden="true"
            />
            <input
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(0);
              }}
              placeholder="Search id, gender, segment"
              aria-label="Search customers"
              className="w-56 rounded-lg border border-surface-700 bg-surface-850 py-1.5 pl-8 pr-3 text-xs text-slate-200 placeholder:text-slate-600 focus:border-accent focus:outline-none"
            />
          </label>
          <select
            value={clusterFilter}
            onChange={(event) => {
              const { value } = event.target;
              setClusterFilter(value === 'all' ? 'all' : Number(value));
              setPage(0);
            }}
            aria-label="Filter by segment"
            className="rounded-lg border border-surface-700 bg-surface-850 px-3 py-1.5 text-xs text-slate-200 focus:border-accent focus:outline-none"
          >
            <option value="all">All segments</option>
            {clusters.map((cluster) => (
              <option key={cluster.cluster_id} value={cluster.cluster_id}>
                {cluster.name}
              </option>
            ))}
          </select>
        </div>
      </header>

      <div className="max-h-[32rem] overflow-auto">
        <table className="data-table">
          <thead>
            <tr>
              {COLUMNS.map((column) => (
                <th key={column.key}>
                  {column.sortable ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(column.key as SortKey)}
                      className="flex items-center gap-1 uppercase tracking-wider hover:text-slate-200"
                    >
                      {column.label}
                      {sortKey === column.key ? (
                        ascending ? (
                          <ArrowUp className="h-3 w-3" aria-hidden="true" />
                        ) : (
                          <ArrowDown className="h-3 w-3" aria-hidden="true" />
                        )
                      ) : null}
                    </button>
                  ) : (
                    column.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((customer) => (
              <tr key={customer.customer_id} className="hover:bg-surface-850/60">
                <td className="font-mono text-slate-400">{customer.customer_id}</td>
                <td>{customer.gender}</td>
                <td className="font-mono">{customer.age}</td>
                <td className="font-mono">{formatNumber(customer.annual_income, 1)}</td>
                <td className="font-mono">{formatNumber(customer.spending_score, 1)}</td>
                <td className="font-mono">{customer.cluster_id}</td>
                <td>
                  <span className="flex items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: colorFor.get(customer.cluster_id) ?? '#94a3b8' }}
                      aria-hidden="true"
                    />
                    {customer.cluster_name}
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length} className="px-3 py-8 text-center text-slate-500">
                  No customers match the current filters.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <footer className="flex items-center justify-between border-t border-surface-800 px-5 py-3 text-xs text-slate-500">
        <span>
          Page {currentPage + 1} of {pageCount}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setPage((value) => Math.max(0, value - 1))}
            disabled={currentPage === 0}
            className="chip disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => setPage((value) => Math.min(pageCount - 1, value + 1))}
            disabled={currentPage >= pageCount - 1}
            className="chip disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </footer>
    </section>
  );
}
