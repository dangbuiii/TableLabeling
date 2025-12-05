---

# 🧾 TableLabelingV2.0

**TableLabeling** is a graphical tool for creating and editing table annotations in images, developed with **Python** and **PyQt5**.
The application helps users easily define table structures, supporting tasks such as training table structure recognition models.

---

## 🛠️ Installation and Run

You can install and run the application with the following steps:

1. **Download the source code**

   * Clone:

     ```bash
     git clone https://github.com/your_username/TableLabeling.git
     ```
   * Or download the `.zip` file from GitHub and extract it.

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. Download model files

The tool works with TATR-based models (Table Transformer) for automatic table structure detection.
The application expects the model files to be located inside the model/ directory.

Please download your TATR model file separately (e.g., TATR-v1.1-Fin.pth, TATR-SciTSR.pth, etc.) and place it in the model/ folder as shown below:

project_root/
├── main.py
├── table_editor.py
├── auto_labeling.py
├── model/
│   └── your_tatr_model.pth

4. **Run the application**

   ```bash
   python main.py
   ```

---

📌 Usage Guide
1. Select folders

After opening the application:

Go to File → Select image folder
→ Choose a folder containing images (.png, .jpg, .jpeg, .bmp).

Go to File → Select label folder
→ Choose where generated XML annotations will be saved.

The left panel will list all images along with icon statuses:

❌ Missing label

⚠️ Unchecked label

✅ Checked (saved)

2. Viewing and navigating images

Click any image in the left panel to load it.

Use the scroll wheel to zoom in/out.

Drag with your mouse to pan around the image.

The viewer automatically fits the table editor to the window.

3. Creating and editting table structure label
To manually annotate a table:

Click Create table label in the right panel.

Enter the number of rows and columns.

A grid appears on top of the image.

You can now interact with the cells:

Select cells, rows, column

Merge/unmerge cells (if supported in your TableEditor)

Adjust cell boundaries (drag the borders)

Every change updates the cell list on the right side.

4. Auto-generate table labels using TATR

You can automatically create table annotations using the integrated model.

There are two options:

➤ Auto-create for the current image

Click Auto Create table label
→ The tool runs process_single_image() using your TATR model.
→ The generated XML is automatically loaded into the editor.

➤ Auto-create for all images

Go to Tool → Auto Create all table labels
→ Runs process_folder()
→ A progress dialog appears with:

Status message

Progress bar
→ Automatically closes when finished.

---

## 📂 Project Structure

```
TableLabeling/
├── main.py
├── table_editor.py
├── auto_labeling.py
├── model/
│   └── <your_model_files>.pth
├── requirements.txt
├── README.md
```

---

## 🤝 Contribution

Pull requests and improvements are welcome!
Please open an issue before submitting major changes.

---

## 📄 License

