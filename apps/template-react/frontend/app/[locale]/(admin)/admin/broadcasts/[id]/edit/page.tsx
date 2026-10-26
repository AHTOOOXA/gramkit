'use client';

import { useParams } from 'next/navigation';

import { BroadcastComposer } from '@/components/admin/broadcasts/BroadcastComposer';

/** Admin → Broadcasts → edit one row (returns to its detail page on save). */
export default function AdminBroadcastEditPage() {
  const { id } = useParams<{ id: string }>();
  const n = Number(id);
  return <BroadcastComposer editId={Number.isInteger(n) ? n : null} />;
}
