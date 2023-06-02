ckan.module('gdc_agency_export_package', ($) => {
    return {
        initialize: function () {
            const progressWrapDom = document.getElementById(this.options.progress_id);

            this.el.on('click', (e) => {
                progressWrapDom.style.display = 'block';
                this._updateProgress(0);
                this._processing();
            });
        },
        _processing: async function (page = 1, id = null) {
            const url = `/api/3/action/gdc_agency_export_package?p=${page}`;
            try {

                const raw = await fetch(id !== null ? `${url}&id=${id}` : url);
                const res = await raw.json();

                if (res.result.page < res.result.page_count) {
                    const percent = Math.floor(res.result.page / res.result.page_count * 100);
                    this._updateProgress(percent);
                    this._processing(res.result.page + 1, res.result.file_id)
                } else {
                    document.getElementById(this.options.progress_id).style.display = 'none';
                    this._updateProgress(0);
                    window.location = `/ckan-admin/dataset-export/${res.result.file_id}`
                }

            } catch (e) {
                console.log(e);
                alert('ผิดผลาด');
                location.reload();
            }
        },
        _updateProgress: function (pg) {
            const parentDom = document.getElementById(this.options.progress_id);
            const barDom = parentDom.querySelector('.progress-bar')
            barDom.setAttribute('aria-valuenow', pg);
            barDom.style.width = `${pg}%`;
        }
    };
});
