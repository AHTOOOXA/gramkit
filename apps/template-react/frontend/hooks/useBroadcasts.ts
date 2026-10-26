import { useQueryClient } from '@tanstack/react-query';
import { classifyHttpError } from '@tma-platform/core-react/errors';

import { apiFetch } from '@/config/kubb-config';
import { useCancelBroadcast } from '@/src/gen/hooks/useCancelBroadcast';
import { useCreateBroadcast } from '@/src/gen/hooks/useCreateBroadcast';
import { useEditBroadcast } from '@/src/gen/hooks/useEditBroadcast';
import { getBroadcastQueryKey } from '@/src/gen/hooks/useGetBroadcast';
import { listBroadcastsQueryKey } from '@/src/gen/hooks/useListBroadcasts';
import { useSendBroadcastNow } from '@/src/gen/hooks/useSendBroadcastNow';
import type { BroadcastMediaUploadResponse } from '@/src/gen/models/BroadcastMediaUploadResponse';

export type BroadcastMediaType = 'photo' | 'video' | 'animation' | 'document';

/**
 * useBroadcasts — the admin broadcast mutations (create / edit / cancel /
 * send-now) from the core admin API (`/admin/broadcasts`), the multipart media
 * upload, and cache invalidation for the list and a single broadcast.
 *
 * Media upload goes through `apiFetch` (not the generated axios client) so the
 * browser sets the multipart boundary itself — the generated client's JSON
 * Content-Type would break the upload.
 *
 * Port of template-vue's `useBroadcasts`.
 * TODO: extract to core/frontend-react when a second React app needs this.
 */
export function useBroadcasts() {
  const queryClient = useQueryClient();

  const create = useCreateBroadcast();
  const edit = useEditBroadcast();
  const cancel = useCancelBroadcast();
  const sendNow = useSendBroadcastNow();

  const invalidateList = () =>
    queryClient.invalidateQueries({ queryKey: listBroadcastsQueryKey() });

  const invalidateOne = (id: number) =>
    queryClient.invalidateQueries({ queryKey: getBroadcastQueryKey(id) });

  /**
   * Upload a media file (multipart) and get back the Telegram `file_id` the
   * backend minted for it. `apiFetch` applies the auth header, cookies and
   * base URL; the browser owns the multipart `Content-Type` boundary.
   */
  const uploadMedia = async (
    file: File,
    messageType: BroadcastMediaType
  ): Promise<BroadcastMediaUploadResponse> => {
    const form = new FormData();
    form.append('file', file);
    form.append('message_type', messageType);

    const res = await apiFetch('/admin/broadcasts/media', {
      method: 'POST',
      body: form,
    });
    if (!res.ok) {
      let body: Record<string, unknown> | undefined;
      try {
        body = (await res.json()) as Record<string, unknown>;
      } catch {
        /* non-JSON error body */
      }
      throw classifyHttpError(res.status, body);
    }
    return (await res.json()) as BroadcastMediaUploadResponse;
  };

  return {
    create,
    edit,
    cancel,
    sendNow,
    uploadMedia,
    invalidateList,
    invalidateOne,
  };
}
