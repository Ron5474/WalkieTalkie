export default function Composer({
  input, setInput, onSend, onKeyDown,
  imagePreview, onPickImage, onRemoveImage, fileRef, onFileChange, disabled,
}) {
  return (
    <div className="composer">
      <div className="composer-inner">
        <div className="composer-field">
          {imagePreview && (
            <div className="img-attach-preview">
              <img src={imagePreview} alt="preview" />
              <button className="remove-img" onClick={onRemoveImage}>✕</button>
            </div>
          )}
          <div className="inner-wrap">
            <button className="attach-btn" title="Upload image" onClick={onPickImage}>📷</button>
            <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={onFileChange} />
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask about a city, neighborhood, food spot, or upload a photo..."
              rows={1}
              onInput={(e) => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px'; }}
            />
          </div>
        </div>
        <button className="send-btn" onClick={onSend} disabled={disabled}>↑</button>
      </div>
    </div>
  );
}
