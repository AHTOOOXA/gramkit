import { useQueryClient } from '@tanstack/vue-query';
import { apiFetch } from '@/config/kubb-config';
import { useCreateBroadcast } from '@gen/hooks/useCreateBroadcast';
import { useEditBroadcast } from '@gen/hooks/useEditBroadcast';
import { useCancelBroadcast } from '@gen/hooks/useCancelBroadcast';
import { useSendBroadcastNow } from '@gen/hooks/useSendBroadcastNow';
import { listBroadcastsQueryKey } from '@gen/hooks/useListBroadcasts';
import { getBroadcastQueryKey } from '@gen/hooks/useGetBroadcast';
import type { BroadcastMediaUploadResponse } from '@gen/models/BroadcastMediaUploadResponse';

export type BroadcastMediaType = 'photo' | 'video' | 'animation' | 'document';

/**
 * useBroadcasts — the admin broadcast mutations (create / edit / cancel /
 * send-now) from the core admin API (`/admin/broadcasts`), the multipart media
 * upload, and cache invalidation for the list and a single broadcast.
 *
 * Media upload goes through the raw `apiFetch` util (not the generated axios
 * client) so the browser sets the multipart boundary itself — the generated
 * client's JSON Content-Type would break the upload.
 *
 * TODO: extract to core when a third Vue app needs this.
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
    messageType: BroadcastMediaType,
  ): Promise<BroadcastMediaUploadResponse> => {
    const form = new FormData();
    form.append('file', file);
    form.append('message_type', messageType);

    const res = await apiFetch('/admin/broadcasts/media', { method: 'POST', body: form });
    if (!res.ok) {
      let detail = `Upload failed (${res.status})`;
      try {
        const body = (await res.json()) as { detail?: string };
        if (body?.detail) detail = body.detail;
      } catch {
        /* non-JSON error body */
      }
      throw new Error(detail);
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
